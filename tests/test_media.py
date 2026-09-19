"""Tests for the universal media library (upload, probe, transcribe, extract)."""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import BinaryIO

import pytest

from content_factory.media import (
    MediaLibrary,
    UploadTooLargeError,
    copy_upload_stream,
    detect_kind,
    probe_media,
)
from content_factory.models import MediaKind


@pytest.fixture
def library(tmp_path) -> MediaLibrary:
    return MediaLibrary(tmp_path / "media")


def test_detect_kind_by_extension() -> None:
    assert detect_kind("clip.mp4") == MediaKind.VIDEO
    assert detect_kind("song.mp3") == MediaKind.AUDIO
    assert detect_kind("photo.jpg") == MediaKind.IMAGE
    assert detect_kind("report.pdf") == MediaKind.DOCUMENT
    assert detect_kind("archive.zip") == MediaKind.OTHER


def test_upload_and_retrieve_text_document(library: MediaLibrary) -> None:
    item = library.upload("notes.txt", b"Hello world.\nSecond line.", language="en")
    assert item.kind == MediaKind.DOCUMENT
    assert item.size_bytes == len(b"Hello world.\nSecond line.")
    assert library.get(item.id) is not None
    assert item in library.list_items()


def test_extract_text_from_document(library: MediaLibrary) -> None:
    item = library.upload("guide.txt", b"Alpha\nBeta\nGamma", language="en")
    item = library.extract_text(item.id)
    assert item.text_content == "Alpha\nBeta\nGamma"


def test_transcribe_rejects_non_media(library: MediaLibrary) -> None:
    item = library.upload("doc.txt", b"just text", language="en")
    with pytest.raises(ValueError):
        library.transcribe(item.id)


def test_upload_video_probes_metadata(library: MediaLibrary) -> None:
    # A tiny real WebM so ffprobe has something to read.
    import shutil
    import subprocess

    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg not available")
    out = library._dir / "files" / "tiny.webm"
    out.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=320x240:r=10:d=1",
            "-c:v",
            "libvpx-vp9",
            "-deadline",
            "realtime",
            "-cpu-used",
            "8",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    content = out.read_bytes()
    item = library.upload("tiny.webm", content, language="en")
    assert item.kind == MediaKind.VIDEO
    assert item.duration_seconds is not None and item.duration_seconds > 0
    assert item.width == 320 and item.height == 240


def test_probe_media_on_a_missing_file_returns_nothing() -> None:
    # No probe binary has to exist for this: an unreadable path is not a crash.
    assert probe_media(Path("/nonexistent/x.webm")) == {}


def test_upload_image_records_its_pixel_size(library: MediaLibrary) -> None:
    """An image is probed like any other media, so the index has its size."""
    from PIL import Image

    source = library._dir / "files" / "pixel_size.png"
    source.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (321, 200), (10, 20, 30)).save(source)
    if not probe_media(source).get("width"):
        pytest.skip("no ffprobe/ffmpeg available to measure the file")

    item = library.upload("photo.png", source.read_bytes(), language="en")

    assert item.kind == MediaKind.IMAGE
    assert (item.width, item.height) == (321, 200)
    # A still has no duration; a zero would make it look like a 0-second clip.
    assert item.duration_seconds is None


def test_delete_removes_item(library: MediaLibrary) -> None:
    item = library.upload("a.txt", b"x", language="en")
    assert library.delete(item.id) is True
    assert library.get(item.id) is None
    assert library.delete(item.id) is False


def test_convert_video_to_mp4(library: MediaLibrary) -> None:
    import shutil
    import subprocess

    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg not available")
    out = library._dir / "files" / "tiny.webm"
    out.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=320x240:r=10:d=1",
            "-c:v",
            "libvpx-vp9",
            "-deadline",
            "realtime",
            "-cpu-used",
            "8",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    item = library.upload("tiny.webm", out.read_bytes(), language="en")

    converted = library.convert(item.id, "mp4")
    assert converted.kind == MediaKind.VIDEO
    assert converted.filename.endswith(".mp4")
    assert converted.id != item.id  # original preserved
    assert library.get(item.id) is not None  # original still present
    assert converted.size_bytes > 0


def test_convert_rejects_unknown_format(library: MediaLibrary) -> None:
    import pytest as pt

    item = library.upload("a.txt", b"x", language="en")
    with pt.raises(ValueError):
        library.convert(item.id, "xyz")


def test_copy_upload_stream_writes_exact_bytes(tmp_path) -> None:
    dest = tmp_path / "out" / "data.bin"
    dest.parent.mkdir(parents=True)
    payload = b"stream-payload" * 1000
    source: BinaryIO = io.BytesIO(payload)
    written = copy_upload_stream(source, dest, chunk_bytes=64, max_bytes=10**6)
    assert written == len(payload)
    assert dest.read_bytes() == payload


def test_copy_upload_stream_enforces_max_bytes_exact_boundary(tmp_path) -> None:
    dest = tmp_path / "out" / "data.bin"
    dest.parent.mkdir(parents=True)
    assert (
        copy_upload_stream(io.BytesIO(b"x" * 16), dest, chunk_bytes=8, max_bytes=16)
        == 16
    )
    with pytest.raises(UploadTooLargeError):
        copy_upload_stream(io.BytesIO(b"x" * 17), dest, chunk_bytes=8, max_bytes=16)
    assert dest.read_bytes() == b"x" * 16


def test_copy_upload_stream_cleans_temp_file_on_failure(tmp_path) -> None:
    dest = tmp_path / "out" / "data.bin"
    dest.parent.mkdir(parents=True)

    class Exploding(io.BytesIO):
        def read(self, size: int = -1) -> bytes:
            data = super().read(size)
            if data:
                raise OSError("disk exploded")
            return data

    with pytest.raises(OSError):
        copy_upload_stream(Exploding(b"0123456789"), dest, chunk_bytes=4, max_bytes=100)
    assert not dest.exists()
    assert list(dest.parent.glob(".*.tmp")) == []


def test_upload_stream_rejects_oversize_and_keeps_index_clean(tmp_path) -> None:
    lib = MediaLibrary(tmp_path / "media", max_bytes=10)
    with pytest.raises(UploadTooLargeError):
        lib.upload_stream("clip.mp4", io.BytesIO(b"x" * 11))
    assert lib.list_items() == []
    index = lib._index_path
    assert not index.exists() or json.loads(index.read_text(encoding="utf-8")) == []
    assert list((lib._dir / "files").glob("*")) == []


def test_upload_zero_length_preserves_current_semantics(tmp_path) -> None:
    lib = MediaLibrary(tmp_path / "media")
    item = lib.upload_stream("empty.txt", io.BytesIO(b""))
    assert item.size_bytes == 0
    assert item.kind == MediaKind.DOCUMENT
    assert lib.get(item.id) is not None
    assert lib.path_for(item) is not None and lib.path_for(item).stat().st_size == 0


def test_upload_bytes_wrapper_matches_stream_path(tmp_path) -> None:
    lib = MediaLibrary(tmp_path / "media")
    from_bytes = lib.upload("clip.mp4", b"payload-123", language="vi")
    from_stream = lib.upload_stream(
        "clip.mp4", io.BytesIO(b"payload-123"), language="vi"
    )
    assert from_bytes.size_bytes == from_stream.size_bytes == len(b"payload-123")
    assert from_bytes.mime == from_stream.mime
    assert from_bytes.kind == from_stream.kind == MediaKind.VIDEO


def test_download_from_url_fallback(tmp_path) -> None:
    from unittest.mock import MagicMock, patch

    lib = MediaLibrary(tmp_path / "media")
    mock_resp = MagicMock()
    mock_resp.read.side_effect = [b"fake-mp4-data", b""]
    mock_resp.__enter__.return_value = mock_resp

    with patch("yt_dlp.YoutubeDL", side_effect=Exception("yt-dlp failed")):
        with patch("urllib.request.urlopen", return_value=mock_resp):
            item = lib.download_from_url("https://example.com/video.mp4", language="vi")
            assert item.filename == "video.mp4"
            assert item.kind == MediaKind.VIDEO
            assert item.source == "url:https://example.com/video.mp4"
            assert item.size_bytes == len(b"fake-mp4-data")
