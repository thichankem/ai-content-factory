"""Universal media library: upload anything, probe it, and let AI read it.

Supports video, audio, image, and document upload. Every item is probed with
ffprobe for duration/resolution, and video/audio can be transcribed with
faster-whisper so AI agents can read and re-cook the content. Documents are
extracted to plain text with pypdf. A small royalty-free music-bed generator is
included so a re-cooked cut can change its soundtrack without any external
asset.
"""

from __future__ import annotations

import contextlib
import json
import mimetypes
import shutil
import subprocess
import tempfile
import threading
import uuid
from io import BytesIO
from pathlib import Path
from typing import Any, BinaryIO, TypedDict

from .cache import ContentCache
from .config import (
    DEFAULT_STREAM_CHUNK_BYTES,
    DEFAULT_UPLOAD_MAX_BYTES,
    validate_stream_chunk_bytes,
    validate_upload_max_bytes,
)
from .hardware import require_ffmpeg, resolve_ffprobe
from .models import (
    MediaItem,
    MediaKind,
    TranscriptSegment,
    YouTubeSearchResult,
    utcnow,
)
from .resources import JobKind, ResourceGovernor, default_governor

_VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v", ".flv", ".wmv", ".ts"}
_AUDIO_EXT = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".opus", ".wma"}
_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg", ".tiff"}
_DOC_EXT = {".pdf", ".txt", ".md", ".csv", ".json", ".srt", ".vtt"}


class UploadTooLargeError(ValueError):
    pass


def copy_upload_stream(
    stream: BinaryIO,
    destination: Path,
    *,
    chunk_bytes: int = DEFAULT_STREAM_CHUNK_BYTES,
    max_bytes: int = DEFAULT_UPLOAD_MAX_BYTES,
) -> int:
    validate_stream_chunk_bytes(chunk_bytes)
    validate_upload_max_bytes(max_bytes)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as output:
            temporary = Path(output.name)
            total = 0
            while True:
                chunk = stream.read(min(chunk_bytes, max_bytes - total + 1))
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise UploadTooLargeError(f"Upload exceeds {max_bytes} bytes.")
                output.write(chunk)
        temporary.replace(destination)
        return total
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def detect_kind(filename: str) -> MediaKind:
    """Classify a filename into a media kind by extension."""
    ext = Path(filename).suffix.lower()
    if ext in _VIDEO_EXT:
        return MediaKind.VIDEO
    if ext in _AUDIO_EXT:
        return MediaKind.AUDIO
    if ext in _IMAGE_EXT:
        return MediaKind.IMAGE
    if ext in _DOC_EXT:
        return MediaKind.DOCUMENT
    return MediaKind.OTHER


def resolve_kind(filename: str, probe: dict | None = None) -> MediaKind:
    """The kind a file really is: probed streams first, extension second.

    The extension lies often enough to matter — a library scan found four
    items registered as ``video`` whose only stream was audio (``.mp4``/
    ``.webm`` containers holding a soundtrack) and one 108-byte ``.png`` that
    was not an image at all. Anything built on that classification then
    misbehaved: re-encoding a "video" with no video stream failed, and the
    palette/collage tools choked on the fake image.

    Only a *successful* probe is trusted (``probe['streams_known']``): when
    ffprobe is missing or the file cannot be read, the extension stays the
    answer, because guessing ``other`` for everything would be worse than the
    problem this solves.
    """
    kind = detect_kind(filename)
    if not probe or not probe.get("streams_known"):
        return kind
    has_video = bool(probe.get("has_video"))
    has_audio = bool(probe.get("has_audio"))
    if kind is MediaKind.VIDEO and not has_video:
        return MediaKind.AUDIO if has_audio else MediaKind.OTHER
    if kind is MediaKind.AUDIO and not has_audio:
        return MediaKind.VIDEO if has_video else MediaKind.OTHER
    return kind


#: First bytes that give away a web page or an error body rather than media.
_TEXT_PAYLOAD_PREFIXES = (b"<!doctype", b"<html", b"<?xml", b"<head", b'{"', b"{\n")


class DownloadRejectedError(ValueError):
    """Raised when a URL that was asked for media did not return media."""


def _looks_like_text_payload(path: Path) -> bool:
    """Whether a downloaded file starts like a page instead of a container."""
    try:
        with path.open("rb") as handle:
            head = handle.read(512).lstrip().lower()
    except OSError:  # pragma: no cover - an unreadable file is caught elsewhere
        return False
    return head.startswith(_TEXT_PAYLOAD_PREFIXES)


def _require_media_payload(content_type: Any, url: str) -> None:
    """Refuse a raw download whose Content-Type is not media.

    A server may omit the header entirely; only a *stated* non-media type is
    refused here, because the file itself is checked afterwards anyway.
    """
    if not isinstance(content_type, str):
        return
    kind = content_type.split(";")[0].strip().lower()
    if kind.startswith("text/") or kind in {"application/json", "application/xml"}:
        msg = (
            f"{url} answered with '{kind or 'no content type'}', not audio or "
            "video. The link is not a direct media URL (or the site blocked the "
            "request); use a direct file URL or a supported video link."
        )
        raise DownloadRejectedError(msg)


def _require_media_file(path: Path, url: str) -> None:
    """Refuse a downloaded file that holds no audio or video stream."""
    if _looks_like_text_payload(path):
        msg = (
            f"{url} returned a web page, not media "
            f"({path.stat().st_size} bytes starting with markup). The extractor "
            "was blocked or the link is not a media URL."
        )
        raise DownloadRejectedError(msg)
    meta = probe_media(path)
    if meta.get("streams_known") and not (meta["has_video"] or meta["has_audio"]):
        msg = (
            f"{url} downloaded {path.stat().st_size} bytes but ffprobe found no "
            "audio or video stream in them."
        )
        raise DownloadRejectedError(msg)


def _parse_vtt_timestamp(value: str) -> float | None:
    """``00:01:02.500`` (or ``01:02.500``) as seconds, or ``None``."""
    parts = value.strip().split(":")
    if not 2 <= len(parts) <= 3:
        return None
    try:
        numbers = [float(part.replace(",", ".")) for part in parts]
    except ValueError:
        return None
    seconds = 0.0
    for number in numbers:
        seconds = seconds * 60 + number
    return round(seconds, 3)


def _vtt_to_segments(vtt: str) -> list[dict[str, float | str]]:
    """Parse a WebVTT file into ``{"start_seconds", "end_seconds", "text"}``.

    Captions are the *instant* transcript path and they already carry the
    timings a subtitle burn-in or a beat-aligned cut needs; throwing them away
    and returning ``segments: []`` next to a full ``text`` made the tool look
    like it had found timecodes it had actually discarded.
    """
    import re

    segments: list[dict[str, float | str]] = []
    start: float | None = None
    end: float | None = None
    lines: list[str] = []

    def flush() -> None:
        text = " ".join(lines).strip()
        if start is not None and end is not None and text:
            segments.append(
                {"start_seconds": start, "end_seconds": end, "text": text}
            )

    for raw in vtt.splitlines():
        line = raw.strip()
        if "-->" in line:
            flush()
            left, _, right = line.partition("-->")
            start = _parse_vtt_timestamp(left.split()[-1] if left.split() else "")
            right_tokens = right.split()
            end = _parse_vtt_timestamp(right_tokens[0]) if right_tokens else None
            lines = []
            continue
        if not line or line.startswith(("WEBVTT", "Kind:", "Language:", "NOTE")):
            continue
        cleaned = re.sub(r"<[^>]+>", "", line)
        if cleaned:
            lines.append(cleaned)
    flush()
    return segments


def _safe_name(filename: str) -> str:
    import re

    return re.sub(r"[^a-zA-Z0-9_.-]", "_", filename).strip("_") or "file"


def probe_media(path: Path) -> dict:
    """Return duration/width/height/streams for a media file using ffprobe.

    ``streams_known`` is the honest part: it is ``True`` only when ffprobe ran
    and understood the file, so a caller can tell "this really is audio-only"
    apart from "nobody could measure this" — see :func:`resolve_kind`.
    """
    binary = resolve_ffprobe()
    if binary is None:
        return {}
    proc = subprocess.run(
        [
            binary,
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=codec_type,width,height",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return {}
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {}
    result: dict = {"streams_known": True, "has_video": False, "has_audio": False}
    fmt = data.get("format") or {}
    try:
        result["duration_seconds"] = float(fmt.get("duration", 0) or 0) or None
    except (TypeError, ValueError):
        result["duration_seconds"] = None
    for stream in data.get("streams") or []:
        codec_type = stream.get("codec_type")
        if codec_type == "video":
            result["has_video"] = True
            if result.get("width") is None:
                result["width"] = stream.get("width")
                result["height"] = stream.get("height")
        elif codec_type == "audio":
            result["has_audio"] = True
    return result


#: Target formats the media library can convert to (ffmpeg args + output kind).
class _ConvertSpec(TypedDict):
    ext: str
    kind: MediaKind
    args: list[str]


CONVERT_TARGETS: dict[str, _ConvertSpec] = {
    "mp4": {
        "ext": "mp4",
        "kind": MediaKind.VIDEO,
        "args": [
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
        ],
    },
    "webm": {
        "ext": "webm",
        "kind": MediaKind.VIDEO,
        "args": [
            "-c:v",
            "libvpx-vp9",
            "-deadline",
            "realtime",
            "-cpu-used",
            "8",
            "-b:v",
            "1M",
            "-c:a",
            "libopus",
        ],
    },
    "mp3": {
        "ext": "mp3",
        "kind": MediaKind.AUDIO,
        "args": ["-vn", "-c:a", "libmp3lame", "-b:a", "192k"],
    },
    "wav": {
        "ext": "wav",
        "kind": MediaKind.AUDIO,
        "args": ["-vn", "-c:a", "pcm_s16le"],
    },
    "png": {"ext": "png", "kind": MediaKind.IMAGE, "args": ["-frames:v", "1"]},
    "jpg": {
        "ext": "jpg",
        "kind": MediaKind.IMAGE,
        "args": ["-frames:v", "1", "-q:v", "2"],
    },
}


def convert_file(
    src: Path,
    dst: Path,
    target_format: str,
    *,
    ffmpeg_binary: str | None = None,
) -> Path:
    """Convert a media file to another format with ffmpeg."""
    binary = require_ffmpeg(ffmpeg_binary, purpose="media conversion")
    fmt = target_format.lower().lstrip(".")
    if fmt not in CONVERT_TARGETS:
        raise ValueError(f"Unsupported target format '{fmt}'.")
    dst.parent.mkdir(parents=True, exist_ok=True)
    args = list(CONVERT_TARGETS[fmt]["args"])
    command = [binary, "-y", "-i", str(src), *args, str(dst)]
    proc = subprocess.run(command, capture_output=True, text=True, check=False)
    if proc.returncode != 0 or not dst.is_file() or dst.stat().st_size == 0:
        detail = proc.stderr.strip().splitlines()[-1:] or ["ffmpeg conversion failed"]
        raise RuntimeError(detail[0])
    return dst


class MediaLibrary:
    """Process-local, disk-backed store of universally uploaded media."""

    def __init__(
        self,
        media_dir: str | Path,
        cache: ContentCache | None = None,
        *,
        chunk_bytes: int = DEFAULT_STREAM_CHUNK_BYTES,
        max_bytes: int = DEFAULT_UPLOAD_MAX_BYTES,
        governor: ResourceGovernor | None = None,
        transcribe_model: str = "base",
        transcribe_device: str = "auto",
        storage: Any | None = None,
    ) -> None:
        validate_stream_chunk_bytes(chunk_bytes)
        validate_upload_max_bytes(max_bytes)
        self._chunk_bytes = chunk_bytes
        self._max_bytes = max_bytes
        # Speech-to-text goes through the governor: one heavy job at a time, and
        # the GPU only when a CUDA build of torch is actually installed.
        self._governor = governor
        self._transcribe_model = transcribe_model
        self._transcribe_device = transcribe_device
        self._dir = Path(media_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self._dir / "index.json"
        self._lock = threading.RLock()
        self._items: dict[str, MediaItem] = {}
        # Raw caption files by (url, language): the timings of a transcript
        # survive the temporary download directory that produced them.
        self._caption_cache: dict[str, str] = {}
        self._cache = cache
        # Authoritative media-file store. Local disk by default; S3 when the
        # caller passes a cloud backend. ``media_dir/files/`` stays the local
        # processing cache either way.
        if storage is None:
            from .cloud import LocalMediaStorage

            storage = LocalMediaStorage(self._dir / "files")
        self._storage = storage
        self._load()

    # --- persistence ----------------------------------------------------------

    def _load(self) -> None:
        if not self._index_path.is_file():
            return
        try:
            data = json.loads(self._index_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        for raw in data:
            try:
                item = MediaItem(**raw)
                self._items[item.id] = item
            except Exception:  # noqa: BLE001 - tolerate corrupt entries
                continue

    def _save(self) -> None:
        with self._lock:
            payload = [item.model_dump(mode="json") for item in self._items.values()]
            temporary = self._index_path.with_suffix(".tmp")
            try:
                temporary.write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                temporary.replace(self._index_path)
            finally:
                temporary.unlink(missing_ok=True)

    # --- CRUD -----------------------------------------------------------------

    def upload(
        self,
        filename: str,
        content: bytes,
        *,
        source: str = "upload",
        language: str = "en",
    ) -> MediaItem:
        """Store raw bytes, classify them, probe metadata, and index the item."""
        with BytesIO(content) as stream:
            return self.upload_stream(
                filename, stream, source=source, language=language
            )

    def upload_stream(
        self,
        filename: str,
        stream: BinaryIO,
        *,
        source: str = "upload",
        language: str = "en",
    ) -> MediaItem:
        clean = _safe_name(filename)
        kind = detect_kind(clean)
        item_id = uuid.uuid4().hex[:12]
        dest = self._dir / "files" / f"{item_id}_{clean}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            size = copy_upload_stream(
                stream, dest, chunk_bytes=self._chunk_bytes, max_bytes=self._max_bytes
            )
            mime = mimetypes.guess_type(clean)[0] or "application/octet-stream"
            meta = (
                probe_media(dest) if kind in (MediaKind.VIDEO, MediaKind.AUDIO) else {}
            )
            kind = resolve_kind(clean, meta)
            item = MediaItem(
                id=item_id,
                filename=clean,
                kind=kind,
                mime=mime,
                size_bytes=size,
                url=f"/media/{item_id}/download",
                duration_seconds=meta.get("duration_seconds"),
                width=meta.get("width"),
                height=meta.get("height"),
                language=language,
                source=source,
            )
            with self._lock:
                self._items[item_id] = item
                try:
                    self._save()
                except BaseException:
                    self._items.pop(item_id, None)
                    raise
            # Persist the authoritative copy to the storage backend (local or S3).
            self._storage.save(self._storage_key(item), dest)
            return item
        except BaseException:
            dest.unlink(missing_ok=True)
            raise

    @staticmethod
    def _storage_key(item: MediaItem) -> str:
        return f"media/{item.id}/{item.filename}"

    def download_from_url(
        self,
        url: str,
        *,
        language: str = "vi",
        extract_audio: bool = False,
    ) -> MediaItem:
        """Download an external video or audio by URL.

        Supports YouTube, TikTok, MP4, and direct stream links.

        The result is *verified* before it is indexed: a failed extraction used
        to fall back to fetching the URL raw and storing whatever came back, so
        a blocked YouTube request produced a 795 KB HTML page registered as
        ``kind=video, mime=video/mp4, duration=null`` and reported as success.
        Nothing downstream could use it, and every consumer that trusted the
        kind broke on it. A payload that is not media is now an error.
        """
        import urllib.request
        from urllib.parse import urlparse

        parsed = urlparse(url)
        temp_dir = Path(tempfile.mkdtemp(prefix="cf_media_dl_"))
        target_file: Path | None = None
        target_filename = "downloaded_video.mp4"

        try:
            try:
                import yt_dlp  # type: ignore[import-untyped]

                out_tmpl = str(temp_dir / "%(title).50s_%(id)s.%(ext)s")
                ydl_opts = {
                    "format": (
                        "bestaudio/best"
                        if extract_audio
                        else "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
                    ),
                    "outtmpl": out_tmpl,
                    "quiet": True,
                    "no_warnings": True,
                    "noplaylist": True,
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.extract_info(url, download=True)
                    files = [f for f in temp_dir.glob("*") if f.is_file()]
                    if files:
                        target_file = files[0]
                        target_filename = target_file.name
            except Exception:  # noqa: BLE001 - extraction failure only means no filename was derived
                target_file = None

            if target_file is None or not target_file.is_file():
                req = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": (
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/120.0.0.0 Safari/537.36"
                        )
                    },
                )
                url_path = Path(parsed.path)
                fallback_name = (
                    url_path.name
                    if url_path.suffix in (_VIDEO_EXT | _AUDIO_EXT)
                    else "online_video.mp4"
                )
                target_file = temp_dir / fallback_name
                with (
                    urllib.request.urlopen(req, timeout=30) as resp,
                    target_file.open("wb") as out_f,
                ):
                    _require_media_payload(resp.headers.get("Content-Type", ""), url)
                    shutil.copyfileobj(resp, out_f)
                target_filename = fallback_name

            if target_file is None or not target_file.is_file():
                raise DownloadRejectedError(f"Could not download media from URL: {url}")
            _require_media_file(target_file, url)

            with target_file.open("rb") as f:
                return self.upload_stream(
                    target_filename,
                    f,
                    source=f"url:{url}",
                    language=language,
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def search_youtube(self, query: str, limit: int = 8) -> list[YouTubeSearchResult]:
        """Search YouTube for videos matching ``query`` (metadata only, no download).

        Uses yt-dlp's ``ytsearch`` extractor, which is the same engine that backs
        the download path, so search and download agree on what a video is.
        Returns lightweight, JSON-safe results an agent can pick from.
        """
        import yt_dlp

        limit = max(1, min(int(limit), 25))
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "skip_download": True,
            "extract_flat": "in_playlist",
        }
        results: list[YouTubeSearchResult] = []
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
            for entry in info.get("entries") or []:
                if not entry:
                    continue
                video_id = entry.get("id") or ""
                url = entry.get("webpage_url") or (
                    f"https://www.youtube.com/watch?v={video_id}" if video_id else ""
                )
                results.append(
                    YouTubeSearchResult(
                        id=video_id,
                        title=entry.get("title") or "",
                        url=url,
                        duration_seconds=entry.get("duration"),
                        uploader=entry.get("channel")
                        or entry.get("uploader")
                        or entry.get("channel_id")
                        or "",
                        thumbnail=entry.get("thumbnail") or "",
                        description=(entry.get("description") or "")[:500],
                        view_count=entry.get("view_count"),
                    )
                )
        return results

    # --- Transcript by any means ----------------------------------------------

    def fetch_subtitles(self, url: str, language: str = "en") -> str | None:
        """Fetch a YouTube video's existing subtitles/captions (instant, no model).

        Tries manual captions first, then auto-generated ones, preferring the
        requested language and falling back to English. Returns the joined
        transcript text, or ``None`` when the video has no captions at all.
        """
        import yt_dlp

        temp_dir = Path(tempfile.mkdtemp(prefix="cf_subs_"))
        try:
            langs = [language, "en"]
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": langs,
                "subtitlesformat": "vtt",
                "outtmpl": str(temp_dir / "%(id)s"),
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(url, download=True)
            vtt_files = sorted(temp_dir.glob("*.vtt"))
            if not vtt_files:
                return None
            # Prefer the requested language, then English, then any.
            vtt_files.sort(
                key=lambda p: 0 if language in p.name else (1 if "en" in p.name else 2)
            )
            raw = vtt_files[0].read_text(encoding="utf-8", errors="ignore")
            self._remember_captions(url, language, raw)
            text = self._vtt_to_text(raw)
            return text or None
        except Exception:  # noqa: BLE001 - a subtitle miss just means fall back to whisper
            return None
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def fetch_subtitle_segments(
        self, url: str, language: str = "en"
    ) -> list[dict[str, float | str]]:
        """Timed segments of a video's captions, from the file already fetched.

        ``fetch_subtitles`` is what downloads captions; this reads the cue
        timings out of *that same* file, so it costs nothing when called right
        after and never triggers a second network round trip on a path whose
        whole point is being instant. A caller that never fetched captions gets
        an empty list, not a download.
        """
        raw = self._caption_cache.get(self._caption_key(url, language))
        return _vtt_to_segments(raw) if raw else []

    @staticmethod
    def _caption_key(url: str, language: str) -> str:
        return f"{url}|{language}"

    def _remember_captions(self, url: str, language: str, raw: str) -> None:
        """Keep the last few caption files so their timings stay available."""
        with self._lock:
            self._caption_cache[self._caption_key(url, language)] = raw
            while len(self._caption_cache) > 8:
                self._caption_cache.pop(next(iter(self._caption_cache)))

    @staticmethod
    def _vtt_to_text(vtt: str) -> str:
        """Strip a WebVTT file down to its spoken lines."""
        import re

        lines: list[str] = []
        for raw in vtt.splitlines():
            line = raw.strip()
            if not line or line.startswith("WEBVTT") or "-->" in line:
                continue
            if line.startswith(("Kind:", "Language:", "NOTE")):
                continue
            line = re.sub(r"<[^>]+>", "", line)
            if line:
                lines.append(line)
        return " ".join(lines).strip()

    @staticmethod
    def _youtube_url_from_source(source: str) -> str | None:
        """Extract a YouTube URL from an item's ``url:...`` source, if any."""
        if not source or not source.startswith("url:"):
            return None
        url = source[len("url:") :].strip()
        if "youtube.com" in url or "youtu.be" in url:
            return url
        return None

    def transcribe_youtube(self, url: str, language: str = "en") -> dict:
        """Get a transcript for a YouTube video by any means.

        Strategy 1 — existing subtitles/captions (instant, free, no model).
        Strategy 2 — download the audio and run faster-whisper locally.
        Returns ``{"source", "text", "segments", "has_timestamps", "media_id"}``.

        ``has_timestamps`` is the honest part: caption files are parsed into
        cue timings, but a source that could not be split (or a cached text-only
        transcript) reports ``False`` instead of leaving a caller to discover
        that ``segments`` is empty *after* it trusted them for subtitle timing.
        """
        subs = self.fetch_subtitles(url, language)
        if subs:
            segments = self.fetch_subtitle_segments(url, language)
            return {
                "source": "subtitles",
                "text": subs,
                "segments": segments,
                "has_timestamps": bool(segments),
                "media_id": None,
            }
        item = self.download_from_url(url, language=language, extract_audio=True)
        item = self.transcribe(item.id, language)
        segments = [s.model_dump() for s in item.transcript_segments]
        return {
            "source": "whisper",
            "text": item.transcription,
            "segments": segments,
            "has_timestamps": bool(segments),
            "media_id": item.id,
        }

    def add_item(self, item: MediaItem) -> MediaItem:
        """Register an already-constructed item (e.g. an imported one)."""
        with self._lock:
            self._items[item.id] = item
        self._save()
        return item

    def list_items(self) -> list[MediaItem]:
        with self._lock:
            return sorted(
                self._items.values(), key=lambda i: i.created_at, reverse=True
            )

    def query(
        self,
        *,
        kind: str | None = None,
        tag: str | None = None,
        q: str | None = None,
        source: str | None = None,
        min_duration: float | None = None,
        max_duration: float | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        sort: str = "newest",
    ) -> list[MediaItem]:
        """Query the media database with rich filters (the "database" view).

        Filters by kind, tag, free-text (filename/transcription/text_content/tags),
        source, duration range and creation-date range, then sorts by newest,
        oldest, name, size or duration.
        """
        items = self.list_items()
        if kind:
            items = [i for i in items if i.kind.value == kind]
        if tag:
            needle = tag.strip().lower()
            items = [i for i in items if any(t.lower() == needle for t in i.tags)]
        if source:
            items = [i for i in items if i.source == source]
        if min_duration is not None:
            items = [
                i
                for i in items
                if i.duration_seconds is not None and i.duration_seconds >= min_duration
            ]
        if max_duration is not None:
            items = [
                i
                for i in items
                if i.duration_seconds is not None and i.duration_seconds <= max_duration
            ]
        if date_from:
            from datetime import datetime as _dt

            try:
                lo = _dt.fromisoformat(date_from)
                items = [i for i in items if i.created_at >= lo]
            except ValueError:
                pass
        if date_to:
            from datetime import datetime as _dt

            try:
                hi = _dt.fromisoformat(date_to)
                items = [i for i in items if i.created_at <= hi]
            except ValueError:
                pass
        if q:
            needles = [token.lower() for token in q.split() if token]
            if needles:
                items = [i for i in items if self._matches(i, needles)]
        return self._sort(items, sort)

    @staticmethod
    def _matches(item: MediaItem, needles: list[str]) -> bool:
        haystack = " ".join(
            [
                item.filename,
                item.transcription or "",
                item.text_content or "",
                item.source,
                " ".join(item.tags),
            ]
        ).lower()
        return all(n in haystack for n in needles)

    @staticmethod
    def _sort(items: list[MediaItem], sort: str) -> list[MediaItem]:
        if sort == "oldest":
            return sorted(items, key=lambda i: i.created_at)
        if sort == "name":
            return sorted(items, key=lambda i: i.filename.lower())
        if sort == "size":
            return sorted(items, key=lambda i: i.size_bytes, reverse=True)
        if sort == "duration":
            return sorted(
                items,
                key=lambda i: (i.duration_seconds is None, i.duration_seconds or 0),
                reverse=True,
            )
        return sorted(items, key=lambda i: i.created_at, reverse=True)

    def all_tags(self) -> list[str]:
        """Every distinct tag across the library, sorted."""
        seen: set[str] = set()
        with self._lock:
            for item in self._items.values():
                seen.update(t.strip().lower() for t in item.tags if t.strip())
        return sorted(seen)

    def set_tags(self, media_id: str, tags: list[str]) -> MediaItem:
        """Replace an item's tags (normalised: stripped, lowercased, de-duped)."""
        item = self.require(media_id)
        norm: list[str] = []
        for t in tags:
            clean = t.strip().lower()
            if clean and clean not in norm:
                norm.append(clean)
        item.tags = norm
        return self.update(item)

    def add_tag(self, media_id: str, tag: str) -> MediaItem:
        """Add one tag to an item (idempotent)."""
        item = self.require(media_id)
        clean = tag.strip().lower()
        if clean and clean not in item.tags:
            item.tags.append(clean)
            return self.update(item)
        return item

    def remove_tag(self, media_id: str, tag: str) -> MediaItem:
        """Remove one tag from an item (idempotent)."""
        item = self.require(media_id)
        clean = tag.strip().lower()
        if clean in item.tags:
            item.tags = [t for t in item.tags if t != clean]
            return self.update(item)
        return item

    def stats(self) -> dict[str, Any]:
        """Aggregate counts and sizes across the library (dashboard numbers)."""
        items = self.list_items()
        by_kind: dict[str, int] = {}
        total_bytes = 0
        for item in items:
            by_kind[item.kind.value] = by_kind.get(item.kind.value, 0) + 1
            total_bytes += item.size_bytes
        return {
            "total_items": len(items),
            "total_bytes": total_bytes,
            "by_kind": by_kind,
            "tags": self.all_tags(),
        }

    def get(self, media_id: str) -> MediaItem | None:
        with self._lock:
            return self._items.get(media_id)

    def require(self, media_id: str) -> MediaItem:
        item = self.get(media_id)
        if item is None:
            raise KeyError(f"media item '{media_id}' not found")
        return item

    def path_for(self, item: MediaItem) -> Path | None:
        candidate = self._dir / "files" / f"{item.id}_{item.filename}"
        if candidate.is_file():
            return candidate
        # Not cached locally — pull the authoritative copy from storage (S3).
        key = self._storage_key(item)
        if not self._storage.exists(key):
            return None
        candidate.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self._storage.open(key) as src, candidate.open("wb") as dst:
                shutil.copyfileobj(src, dst)
            return candidate
        except Exception:  # noqa: BLE001 - a fetch failure just means "no file"
            candidate.unlink(missing_ok=True)
            return None

    def delete(self, media_id: str) -> bool:
        with self._lock:
            item = self._items.pop(media_id, None)
        if item is None:
            return False
        path = self.path_for(item)
        if path is not None:
            with contextlib.suppress(OSError):
                path.unlink(missing_ok=True)
        with contextlib.suppress(Exception):  # storage delete is best-effort
            self._storage.delete(self._storage_key(item))
        self._save()
        return True

    def update(self, item: MediaItem) -> MediaItem:
        item.updated_at = utcnow()
        with self._lock:
            self._items[item.id] = item
        self._save()
        return item

    # --- Format conversion ----------------------------------------------------

    def convert(self, media_id: str, target_format: str) -> MediaItem:
        """Convert a media item to another format (mp4/webm/mp3/wav/png/jpg).

        Produces a brand-new sibling MediaItem so the original is preserved.
        """
        item = self.require(media_id)
        src = self.path_for(item)
        if src is None:
            raise FileNotFoundError(f"media file for '{media_id}' is missing")
        fmt = target_format.lower().lstrip(".")
        if fmt not in CONVERT_TARGETS:
            raise ValueError(
                f"Unsupported target format '{fmt}'. Known: {sorted(CONVERT_TARGETS)}"
            )
        spec = CONVERT_TARGETS[fmt]
        clean = _safe_name(item.filename)
        stem = Path(clean).stem or "media"
        converted_id = uuid.uuid4().hex[:12]
        out_name = f"{stem}.{spec['ext']}"
        dest = self._dir / "files" / f"{converted_id}_{out_name}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        convert_file(src, dest, fmt)

        mime = mimetypes.guess_type(dest.name)[0] or "application/octet-stream"
        meta = (
            probe_media(dest)
            if spec["kind"] in (MediaKind.VIDEO, MediaKind.AUDIO)
            else {}
        )
        converted = MediaItem(
            id=converted_id,
            filename=out_name,
            kind=spec["kind"],
            mime=mime,
            size_bytes=dest.stat().st_size,
            url=f"/media/{converted_id}/download",
            duration_seconds=meta.get("duration_seconds"),
            width=meta.get("width"),
            height=meta.get("height"),
            language=item.language,
            source=f"convert:{item.id}:{fmt}",
        )
        with self._lock:
            self._items[converted.id] = converted
        self._save()
        return converted

    # --- AI understanding -----------------------------------------------------

    def transcribe(self, media_id: str, language: str = "en") -> MediaItem:
        """Transcribe a video/audio item with faster-whisper (CPU-capable).

        When a :class:`ContentCache` is attached, the transcript is memoized by
        file-content hash + language, so a retried run resumes instead of
        re-running the model.
        """
        item = self.require(media_id)
        if item.kind not in (MediaKind.VIDEO, MediaKind.AUDIO):
            raise ValueError(f"'{item.kind}' cannot be transcribed; use extract_text")
        if item.transcription:
            return item

        # Strategy 1 — reuse the video's existing subtitles (instant, no model).
        # Tried before the file check because subtitles need only the source URL,
        # not the downloaded file on disk.
        youtube_url = self._youtube_url_from_source(item.source)
        if youtube_url:
            subs = self.fetch_subtitles(youtube_url, language)
            if subs:
                item.transcription = subs
                item.transcript_segments = []
                item.language = language
                return self.update(item)

        path = self.path_for(item)
        if path is None:
            raise FileNotFoundError(f"media file for '{media_id}' is missing")

        def compute() -> tuple[str, list[TranscriptSegment]]:
            return self._run_whisper(path, language)

        if self._cache is not None:
            key = self._cache.key_for_file(
                "transcribe",
                path,
                {"language": language},
                chunk_bytes=self._chunk_bytes,
            )
            hit = self._cache.get_json(key)
            if hit is not None:
                text = str(hit.get("text", ""))
                cues = [
                    TranscriptSegment(**segment) for segment in hit.get("segments", [])
                ]
            else:
                text, cues = compute()
                self._cache.put_json(
                    key,
                    {
                        "text": text,
                        "segments": [segment.model_dump() for segment in cues],
                    },
                )
        else:
            text, cues = compute()

        item.transcription = text
        item.transcript_segments = cues
        item.language = language
        return self.update(item)

    def _run_whisper(
        self, path: Path, language: str
    ) -> tuple[str, list[TranscriptSegment]]:
        """Run faster-whisper on an audio file; return (text, cues).

        Held inside the governor's transcribe slot so the lazy decoder is fully
        consumed before another heavy job is admitted to the GPU.
        """
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:  # pragma: no cover - depends on optional tool
            raise RuntimeError(
                "faster-whisper is not installed; run `pip install faster-whisper` "
                "to enable transcription."
            ) from exc

        governor = self._governor or default_governor()
        with governor.job(JobKind.TRANSCRIBE) as decision:
            device, compute_type, _reason = governor.whisper_compute(
                self._transcribe_device
            )
            if decision.admission.value != "gpu":
                # The GPU was busy, hot or short of VRAM: spend CPU time instead
                # of waiting, and say so rather than silently queueing.
                device, compute_type = "cpu", "int8"
            model = WhisperModel(
                self._transcribe_model, device=device, compute_type=compute_type
            )
            segments, _info = model.transcribe(str(path), language=language)
            lines: list[str] = []
            cues: list[TranscriptSegment] = []
            for seg in segments:
                text = (seg.text or "").strip()
                if not text:
                    continue
                lines.append(text)
                cues.append(
                    TranscriptSegment(
                        start_seconds=round(float(seg.start), 2),
                        end_seconds=round(float(seg.end), 2),
                        text=text,
                    )
                )
            return " ".join(lines), cues

    def transcribe_file(
        self, path: Path, language: str = "en"
    ) -> tuple[str, list[TranscriptSegment]]:
        """Transcribe an arbitrary audio file (no media item) with faster-whisper."""
        return self._run_whisper(Path(path), language)

    def extract_text(self, media_id: str) -> MediaItem:
        """Extract plain text from a document item (PDF/text)."""
        item = self.require(media_id)
        if item.kind != MediaKind.DOCUMENT:
            raise ValueError(f"'{item.kind}' is not a document")
        if item.text_content:
            return item
        path = self.path_for(item)
        if path is None:
            raise FileNotFoundError(f"media file for '{media_id}' is missing")
        ext = path.suffix.lower()
        if ext == ".pdf":
            try:
                import pypdf

                reader = pypdf.PdfReader(str(path))
                text = "\n".join(page.extract_text() or "" for page in reader.pages)
            except Exception as exc:
                raise RuntimeError(f"could not extract PDF text: {exc}") from exc
        else:
            text = path.read_text(encoding="utf-8", errors="replace")
        item.text_content = text.strip()
        return self.update(item)


# --- Royalty-free music bed ---------------------------------------------------


def synthesize_music_bed(
    output_path: Path,
    duration_seconds: float,
    *,
    ffmpeg_binary: str | None = None,
    mood: str = "cinematic",
) -> Path:
    """Generate a simple royalty-free ambient pad with ffmpeg sine oscillators.

    A stacked set of detuned sine tones with slow tremolo produces a
    cinematic drone that is safe to use as a re-cooked cut's new soundtrack.
    """
    binary = require_ffmpeg(ffmpeg_binary, purpose="synthesizing a music bed")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    duration = max(1.0, float(duration_seconds))
    # Three detuned sine oscillators + a soft low octave, amplitude-modulated.
    filters = (
        "aevalsrc=0.08*sin(2*PI*110*t)+0.045*sin(2*PI*110.7*t)"
        "+0.035*sin(2*PI*164.8*t)+0.025*sin(2*PI*55*t)"
        f":d={duration}:s=44100,"
        "tremolo=f=0.15:d=0.4,"
        "lowpass=f=1200,"
        "volume=0.5"
    )
    command = [
        binary,
        "-y",
        "-f",
        "lavfi",
        "-i",
        filters,
        "-t",
        f"{duration:.3f}",
        "-c:a",
        "libvorbis",
        "-q:a",
        "4",
        str(output_path),
    ]
    proc = subprocess.run(command, capture_output=True, text=True, check=False)
    if proc.returncode != 0 or not output_path.is_file():
        raise RuntimeError(f"music bed synthesis failed: {proc.stderr.strip()[-200:]}")
    return output_path
