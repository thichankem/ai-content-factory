"""Universal media library: upload anything, probe it, and let AI read it.

Supports video, audio, image, and document upload. Every item is probed with
ffprobe for duration/resolution, and video/audio can be transcribed with
faster-whisper so AI agents can read and re-cook the content. Documents are
extracted to plain text with pypdf. A small royalty-free music-bed generator is
included so a re-cooked cut can change its soundtrack without any external
asset.
"""

from __future__ import annotations

import json
import mimetypes
import shutil
import subprocess
import tempfile
import threading
import uuid
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, TypedDict

from .cache import ContentCache
from .config import (
    DEFAULT_STREAM_CHUNK_BYTES,
    DEFAULT_UPLOAD_MAX_BYTES,
    validate_stream_chunk_bytes,
    validate_upload_max_bytes,
)
from .models import MediaItem, MediaKind, TranscriptSegment, utcnow

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


def _safe_name(filename: str) -> str:
    import re

    return re.sub(r"[^a-zA-Z0-9_.-]", "_", filename).strip("_") or "file"


def probe_media(path: Path) -> dict:
    """Return duration/width/height for a media file using ffprobe."""
    binary = shutil.which("ffprobe")
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
    result: dict = {}
    fmt = data.get("format") or {}
    try:
        result["duration_seconds"] = float(fmt.get("duration", 0) or 0) or None
    except (TypeError, ValueError):
        result["duration_seconds"] = None
    for stream in data.get("streams") or []:
        if stream.get("codec_type") == "video":
            result["width"] = stream.get("width")
            result["height"] = stream.get("height")
            break
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
    binary = ffmpeg_binary or shutil.which("ffmpeg")
    if binary is None:
        raise RuntimeError("ffmpeg is required for media conversion.")
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
    ) -> None:
        validate_stream_chunk_bytes(chunk_bytes)
        validate_upload_max_bytes(max_bytes)
        self._chunk_bytes = chunk_bytes
        self._max_bytes = max_bytes
        self._dir = Path(media_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self._dir / "index.json"
        self._lock = threading.RLock()
        self._items: dict[str, MediaItem] = {}
        self._cache = cache
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
            return item
        except BaseException:
            dest.unlink(missing_ok=True)
            raise

    def add_item(self, item: MediaItem) -> MediaItem:
        """Register an already-constructed item (e.g. an imported one)."""
        with self._lock:
            self._items[item.id] = item
        self._save()
        return item

    def list(self) -> list[MediaItem]:
        with self._lock:
            return sorted(
                self._items.values(), key=lambda i: i.created_at, reverse=True
            )

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
        return candidate if candidate.is_file() else None

    def delete(self, media_id: str) -> bool:
        with self._lock:
            item = self._items.pop(media_id, None)
        if item is None:
            return False
        path = self.path_for(item)
        if path is not None:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
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
        path = self.path_for(item)
        if path is None:
            raise FileNotFoundError(f"media file for '{media_id}' is missing")

        def compute() -> tuple[str, list[TranscriptSegment]]:
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:  # pragma: no cover - depends on optional tool
                raise RuntimeError(
                    "faster-whisper is not installed; run `pip install faster-whisper` "
                    "to enable transcription."
                ) from exc

            model = WhisperModel("base", device="cpu", compute_type="int8")
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
            except Exception as exc:  # noqa: BLE001
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
    binary = ffmpeg_binary or shutil.which("ffmpeg")
    if binary is None:
        raise RuntimeError("ffmpeg is required to synthesize a music bed.")
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
