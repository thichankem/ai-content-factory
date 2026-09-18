"""Media tool engine: everything an agent needs to *read* and *cut* media.

The whole point of this module is that a text-only model — no vision, no
ears — can operate on real media. So every operation here has two halves:

* a **reading** half that turns a file into structured text the agent can
  reason about (duration, streams, loudness, silence, scene cuts, palette,
  beat grid), and
* a **cutting/composing** half that turns an agent's decision back into a new
  file (trim, split, concat, extract, fade, loop, loudness-normalise, mix
  tracks, compose image layers, collage).

Nothing here knows about projects or the service layer; it is pure media I/O
over ``ffmpeg``/``ffprobe`` plus Pillow, which keeps it hermetic and testable.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

__all__ = [
    "MediaToolError",
    "beat_grid",
    "collage",
    "compose_layers",
    "concat",
    "contact_sheet",
    "cut",
    "describe",
    "extract_audio",
    "extract_frame",
    "fade_audio",
    "loop_audio",
    "loudness",
    "mix_tracks",
    "normalize_loudness",
    "palette",
    "probe",
    "scene_cuts",
    "silence_ranges",
    "split_at",
    "tempo_shift",
    "trim_audio",
]


class MediaToolError(RuntimeError):
    """Raised when a media operation cannot be completed."""


# ---------------------------------------------------------------------------
# Process helpers
# ---------------------------------------------------------------------------


def _binary(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise MediaToolError(f"'{name}' is required but was not found on PATH.")
    return path


def _run(command: list[str]) -> subprocess.CompletedProcess[bytes]:
    proc = subprocess.run(command, capture_output=True, check=False)
    if proc.returncode != 0:
        detail = proc.stderr.decode("utf-8", "replace").strip().splitlines()
        raise MediaToolError(detail[-1] if detail else f"{command[0]} failed")
    return proc


def _require_file(path: str | Path) -> Path:
    resolved = Path(path)
    if not resolved.is_file():
        raise MediaToolError(f"media file not found: '{resolved}'")
    return resolved


def _ensure_parent(path: str | Path) -> Path:
    resolved = Path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


#: Extensions ffprobe reports as a (one-frame) video stream but are stills.
_STILL_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}


def _is_still_image(path: Path) -> bool:
    """True for a still image, which must never be seeked like a video."""
    return path.suffix.lower() in _STILL_SUFFIXES


# ---------------------------------------------------------------------------
# Reading: probe + loudness + silence + cuts + palette
# ---------------------------------------------------------------------------


def _probe_json(path: Path) -> dict[str, Any]:
    proc = _run(
        [
            _binary("ffprobe"),
            "-hide_banner",
            "-loglevel",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path),
        ]
    )
    payload: Any = json.loads(proc.stdout.decode("utf-8", "replace") or "{}")
    return payload if isinstance(payload, dict) else {}


def probe(path: str | Path) -> dict[str, Any]:
    """Technical fingerprint of any media file, as plain JSON data."""
    resolved = _require_file(path)
    data = _probe_json(resolved)
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    fmt = data.get("format", {})

    def _fps(stream: dict[str, Any]) -> float | None:
        raw = stream.get("avg_frame_rate") or stream.get("r_frame_rate") or ""
        if "/" not in raw:
            return None
        num, _, den = raw.partition("/")
        try:
            value = float(num) / float(den)
        except (TypeError, ZeroDivisionError):
            return None
        return round(value, 3) if value else None

    duration = None
    for candidate in (fmt.get("duration"), (video or {}).get("duration")):
        if candidate not in (None, "N/A"):
            duration = round(float(candidate), 3)
            break

    return {
        "path": str(resolved),
        "name": resolved.name,
        "size_bytes": resolved.stat().st_size,
        "format": fmt.get("format_name"),
        "duration_seconds": duration,
        "bit_rate": (
            int(fmt["bit_rate"]) if str(fmt.get("bit_rate", "")).isdigit() else None
        ),
        "has_video": video is not None,
        "has_audio": audio is not None,
        "width": (video or {}).get("width"),
        "height": (video or {}).get("height"),
        "fps": _fps(video) if video else None,
        "video_codec": (video or {}).get("codec_name"),
        "audio_codec": (audio or {}).get("codec_name"),
        "sample_rate": (
            int(audio["sample_rate"]) if audio and audio.get("sample_rate") else None
        ),
        "channels": (audio or {}).get("channels"),
    }


_LUFS_RE = re.compile(r"I:\s*(-?\d+(?:\.\d+)?)\s*LUFS")
_PEAK_RE = re.compile(r"Peak:\s*(-?\d+(?:\.\d+)?)\s*dBFS")


def loudness(path: str | Path, *, target_lufs: float = -14.0) -> dict[str, Any]:
    """Integrated loudness and true peak (EBU R128), plus distance to target."""
    resolved = _require_file(path)
    proc = _run(
        [
            _binary("ffmpeg"),
            "-hide_banner",
            "-nostats",
            "-i",
            str(resolved),
            "-af",
            "ebur128=peak=true:framelog=quiet",
            "-f",
            "null",
            "-",
        ]
    )
    text = proc.stderr.decode("utf-8", "replace")
    lufs = [float(m.group(1)) for m in _LUFS_RE.finditer(text)]
    peaks = [float(m.group(1)) for m in _PEAK_RE.finditer(text)]
    integrated = lufs[-1] if lufs else None
    peak = max(peaks) if peaks else None
    return {
        "path": str(resolved),
        "integrated_lufs": integrated,
        "true_peak_db": peak,
        "target_lufs": target_lufs,
        "gain_to_target_db": (
            round(target_lufs - integrated, 2) if integrated is not None else None
        ),
        "clipping": peak is not None and peak > -0.1,
    }


_SILENCE_START = re.compile(r"silence_start:\s*(-?\d+(?:\.\d+)?)")
_SILENCE_END = re.compile(r"silence_end:\s*(-?\d+(?:\.\d+)?)")


def silence_ranges(
    path: str | Path,
    *,
    threshold_db: float = -32.0,
    min_seconds: float = 0.35,
) -> list[dict[str, float]]:
    """Detect silent gaps with ffmpeg's ``silencedetect`` filter."""
    resolved = _require_file(path)
    proc = _run(
        [
            _binary("ffmpeg"),
            "-hide_banner",
            "-nostats",
            "-i",
            str(resolved),
            "-af",
            f"silencedetect=noise={threshold_db}dB:d={min_seconds}",
            "-f",
            "null",
            "-",
        ]
    )
    text = proc.stderr.decode("utf-8", "replace")
    starts = [float(m.group(1)) for m in _SILENCE_START.finditer(text)]
    ends = [float(m.group(1)) for m in _SILENCE_END.finditer(text)]
    ranges: list[dict[str, float]] = []
    for index, start in enumerate(starts):
        end = ends[index] if index < len(ends) else None
        if end is None:
            info = probe(resolved)
            end = info["duration_seconds"] or start
        ranges.append(
            {
                "start_seconds": round(max(0.0, start), 3),
                "end_seconds": round(end, 3),
                "duration_seconds": round(max(0.0, end - start), 3),
            }
        )
    return ranges


def scene_cuts(path: str | Path, *, threshold: float = 30.0) -> list[dict[str, Any]]:
    """Shot boundaries as structured text (no vision model required)."""
    from .vision import detect_scene_cuts

    resolved = _require_file(path)
    cuts = detect_scene_cuts(resolved, threshold=threshold)
    return [
        {
            "index": index,
            "start_seconds": round(cut.start_seconds, 3),
            "end_seconds": round(cut.end_seconds, 3),
            "duration_seconds": round(cut.end_seconds - cut.start_seconds, 3),
        }
        for index, cut in enumerate(cuts)
    ]


def palette(path: str | Path, *, count: int = 5, at_seconds: float = 1.0) -> list[str]:
    """Dominant colours as hex strings, so "the look" is text an agent can use."""
    from .image_engine import load_image

    resolved = _require_file(path)
    if _is_still_image(resolved):
        data = resolved.read_bytes()
    else:
        info = probe(resolved)
        moment = min(at_seconds, (info["duration_seconds"] or 1.0) / 2)
        tmp = Path(_temp_path("palette", "png"))
        try:
            extract_frame(resolved, moment, tmp)
            data = tmp.read_bytes()
        finally:
            tmp.unlink(missing_ok=True)
    image = load_image(data).convert("RGB")
    small = image.resize((64, 64))
    quantized = small.quantize(colors=max(1, min(count, 16)), method=2)
    colours = quantized.getpalette() or []
    used = sorted(quantized.getcolors() or [], reverse=True)
    result: list[str] = []
    for _, raw_index in used[:count]:
        index = int(str(raw_index))
        rgb = colours[index * 3 : index * 3 + 3]
        if len(rgb) == 3:
            result.append("#{:02x}{:02x}{:02x}".format(*rgb))
    return result


def _temp_path(stem: str, suffix: str) -> str:
    """Reserve a unique temp path that is free for ffmpeg/Pillow to write."""
    import os
    import tempfile

    handle, name = tempfile.mkstemp(prefix=f"{stem}-", suffix=f".{suffix}")
    os.close(handle)
    Path(name).unlink(missing_ok=True)
    return name


def _energy_envelope(
    path: Path, *, frame_seconds: float = 0.02
) -> tuple[np.ndarray, float]:
    """Short-window RMS envelope used for beat picking (pure numpy)."""
    from .perception import _decode_mono_pcm

    samples, rate = _decode_mono_pcm(path)
    if len(samples) == 0:
        return np.zeros(0, dtype=np.float32), 0.0
    hop = max(1, int(round(frame_seconds * rate)))
    frames = max(1, len(samples) // hop)
    energy = np.empty(frames, dtype=np.float32)
    for index in range(frames):
        chunk = samples[index * hop : (index + 1) * hop]
        energy[index] = float(np.sqrt(np.mean(chunk**2))) if chunk.size else 0.0
    return energy, frame_seconds


def beat_grid(
    path: str | Path,
    *,
    bpm: float | None = None,
    max_beats: int = 512,
) -> dict[str, Any]:
    """Tempo plus beat timestamps, so an agent can cut *on* the music.

    Tempo comes from the acoustic analysis in :mod:`content_factory.perception`;
    beat positions are the local energy peaks nearest each beat interval. The
    result is a plain list of seconds an agent can feed straight into
    ``split_media`` or ``cut_media``.
    """
    from .perception import classify_music_mood

    resolved = _require_file(path)
    if bpm is None:
        mood = classify_music_mood(resolved)
        bpm = float(mood.tempo_bpm) or 120.0
    tempo = max(30.0, min(300.0, float(bpm)))
    interval = 60.0 / tempo
    info = probe(resolved)
    duration = info["duration_seconds"] or 0.0

    energy, frame_seconds = _energy_envelope(resolved)
    beats: list[float] = []
    if energy.size:
        search = max(1, int(round(0.35 * interval / frame_seconds)))
        index = 0
        while index * frame_seconds < duration and len(beats) < max_beats:
            centre = int(round(index * interval / frame_seconds))
            lo = max(0, centre - search)
            hi = min(energy.size, centre + search + 1)
            if hi <= lo:
                break
            window = energy[lo:hi]
            peak = lo + int(np.argmax(window))
            timestamp = round(peak * frame_seconds, 3)
            if not beats or timestamp > beats[-1]:
                beats.append(timestamp)
            index += 1
    return {
        "path": str(resolved),
        "bpm": round(tempo, 2),
        "beat_seconds": round(interval, 4),
        "duration_seconds": round(duration, 3),
        "beats": beats,
        "bar_seconds": round(interval * 4, 4),
        "downbeats": beats[::4],
    }


def describe(path: str | Path, *, include: list[str] | None = None) -> dict[str, Any]:
    """Everything a text-only agent needs to reason about a media file.

    One call answers: how long is it, what is in it, how loud is it, where are
    the silences, where are the shot changes, what is the colour palette, and
    what is the tempo. Optional sections (``include``) cover the slower passes
    (``cuts``, ``palette``, ``beats``, ``loudness``, ``silence``, ``text``).
    """
    resolved = _require_file(path)
    wanted = set(include or ["loudness", "silence", "cuts", "palette", "beats", "text"])
    report: dict[str, Any] = {"probe": probe(resolved)}
    info = report["probe"]

    if "loudness" in wanted and info["has_audio"]:
        try:
            report["loudness"] = loudness(resolved)
        except MediaToolError as exc:  # pragma: no cover - tool dependent
            report["loudness"] = {"error": str(exc)}
    if "silence" in wanted and info["has_audio"]:
        try:
            report["silence"] = silence_ranges(resolved)
        except MediaToolError as exc:  # pragma: no cover - tool dependent
            report["silence"] = {"error": str(exc)}
    if "cuts" in wanted and info["has_video"]:
        try:
            report["scene_cuts"] = scene_cuts(resolved)
        except MediaToolError as exc:  # pragma: no cover - tool dependent
            report["scene_cuts"] = {"error": str(exc)}
    if "palette" in wanted and (
        info["has_video"]
        or resolved.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
    ):
        try:
            report["palette"] = palette(resolved)
        except Exception as exc:  # noqa: BLE001 - perception must never break a read
            report["palette"] = {"error": str(exc)}
    if "beats" in wanted and info["has_audio"]:
        try:
            grid = beat_grid(resolved)
            report["music"] = {
                "bpm": grid["bpm"],
                "beat_seconds": grid["beat_seconds"],
                "bar_seconds": grid["bar_seconds"],
                "beat_count": len(grid["beats"]),
                "first_beats": grid["beats"][:16],
            }
        except Exception as exc:  # noqa: BLE001 - keep the rest of the report
            report["music"] = {"error": str(exc)}
    if "text" in wanted:
        report["text"] = ocr_text(resolved)
    return report


def ocr_text(path: str | Path) -> dict[str, Any]:
    """Read words out of an image/video frame using ``tesseract`` or ``easyocr``."""
    resolved = _require_file(path)
    binary = shutil.which("tesseract")
    target = resolved
    temporary: Path | None = None
    info = probe(resolved)
    if info["has_video"]:
        temporary = Path(_temp_path("ocr", "png"))
        extract_frame(
            resolved, min(1.0, (info["duration_seconds"] or 1.0) / 2), temporary
        )
        target = temporary

    if binary is not None:
        try:
            proc = _run([binary, str(target), "stdout", "--psm", "6"])
            text = proc.stdout.decode("utf-8", "replace").strip()
            return {
                "available": True,
                "text": text,
                "words": len(text.split()),
                "engine": "tesseract",
            }
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    # Fallback to local AI OCR model (EasyOCR)
    try:
        import easyocr  # type: ignore[import-untyped]

        reader = easyocr.Reader(["en"], gpu=False, verbose=False)
        results = reader.readtext(str(target))
        lines = [str(item[1]) for item in results if len(item) > 1]
        text = "\n".join(lines).strip()
        elements = [
            {
                "text": str(item[1]),
                "confidence": round(float(item[2]), 3) if len(item) > 2 else 1.0,
            }
            for item in results
            if len(item) > 1
        ]
        return {
            "available": True,
            "text": text,
            "words": len(text.split()),
            "engine": "easyocr",
            "elements": elements,
        }
    except ImportError:
        return {
            "available": False,
            "reason": "neither tesseract nor easyocr installed",
            "hint": "install tesseract or pip install easyocr to read on-screen text",
        }
    except Exception as exc:  # noqa: BLE001
        return {"available": False, "error": str(exc)}
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Cutting: trim, split, concat, extract
# ---------------------------------------------------------------------------


def _reencode_args(suffix: str) -> list[str]:
    if suffix.lower() in {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}:
        return ["-vn"]
    return [
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "160k",
        "-movflags",
        "+faststart",
    ]


def cut(
    source: str | Path,
    start_seconds: float,
    end_seconds: float,
    destination: str | Path,
    *,
    copy: bool = True,
) -> dict[str, Any]:
    """Cut ``[start, end)`` out of any media file into a new file."""
    src = _require_file(source)
    dst = _ensure_parent(destination)
    start = max(0.0, float(start_seconds))
    duration = float(end_seconds) - start
    if duration <= 0:
        raise MediaToolError("end_seconds must be greater than start_seconds.")
    command = [
        _binary("ffmpeg"),
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        f"{start:.3f}",
        "-i",
        str(src),
        "-t",
        f"{duration:.3f}",
    ]
    command.extend(["-c", "copy"] if copy else _reencode_args(dst.suffix))
    command.append(str(dst))
    try:
        _run(command)
    except MediaToolError:
        if not copy:
            raise
        # Stream copy fails when the requested range cannot be cut on a
        # keyframe; re-encode that range instead of returning nothing.
        _run(
            [
                _binary("ffmpeg"),
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                f"{start:.3f}",
                "-i",
                str(src),
                "-t",
                f"{duration:.3f}",
                *_reencode_args(dst.suffix),
                str(dst),
            ]
        )
    return {
        "source": str(src),
        "destination": str(dst),
        "start_seconds": round(start, 3),
        "end_seconds": round(start + duration, 3),
        "duration_seconds": round(duration, 3),
        "size_bytes": dst.stat().st_size,
    }


def split_at(
    source: str | Path,
    timestamps: Sequence[float],
    destination_dir: str | Path,
    *,
    prefix: str = "clip",
    copy: bool = True,
) -> list[dict[str, Any]]:
    """Cut one file at every timestamp into numbered clips."""
    src = _require_file(source)
    info = probe(src)
    duration = info["duration_seconds"] or 0.0
    points = sorted({round(max(0.0, float(t)), 3) for t in timestamps})
    points = [p for p in points if 0 < p < duration]
    out_dir = Path(destination_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    bounds = [0.0, *points, duration]
    clips: list[dict[str, Any]] = []
    for index, (start, end) in enumerate(zip(bounds, bounds[1:], strict=False)):
        if end - start < 0.05:
            continue
        target = out_dir / f"{prefix}_{index + 1:03d}{src.suffix}"
        report = cut(src, start, end, target, copy=copy)
        report["index"] = index + 1
        clips.append(report)
    return clips


def _demuxer_uri(path: Path) -> str:
    """Absolute path as the concat demuxer needs it.

    Windows drive letters look like a URL scheme to ffmpeg (``C:`` reads as a
    protocol), so those paths are prefixed with an explicit ``file:`` scheme;
    POSIX paths are already unambiguous.
    """
    uri = path.resolve().as_posix()
    return uri if uri.startswith("/") else f"file:{uri}"


def concat(
    sources: Sequence[str | Path],
    destination: str | Path,
    *,
    copy: bool = True,
) -> dict[str, Any]:
    """Join clips in order into one file (fast copy, or filtered re-encode)."""
    if not sources:
        raise MediaToolError("concat needs at least one source file.")
    paths = [_require_file(p) for p in sources]
    dst = _ensure_parent(destination)
    listing = Path(_temp_path("concat", "txt"))
    listing.write_text(
        "\n".join(f"file '{_demuxer_uri(path)}'" for path in paths) + "\n",
        encoding="utf-8",
    )
    try:
        command = [
            _binary("ffmpeg"),
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(listing),
        ]
        command.extend(["-c", "copy"] if copy else _reencode_args(dst.suffix))
        command.append(str(dst))
        try:
            _run(command)
        except MediaToolError:
            _run(
                [
                    _binary("ffmpeg"),
                    "-y",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    str(listing),
                    *_reencode_args(dst.suffix),
                    str(dst),
                ]
            )
    finally:
        listing.unlink(missing_ok=True)
    return {
        "destination": str(dst),
        "clips": [str(path) for path in paths],
        "count": len(paths),
        "duration_seconds": probe(dst)["duration_seconds"],
        "size_bytes": dst.stat().st_size,
    }


def extract_audio(source: str | Path, destination: str | Path) -> dict[str, Any]:
    """Pull the audio track out of a video (or re-wrap an audio file)."""
    src = _require_file(source)
    dst = _ensure_parent(destination)
    command = [
        _binary("ffmpeg"),
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(src),
        "-vn",
    ]
    if dst.suffix.lower() == ".wav":
        command.extend(["-c:a", "pcm_s16le"])
    else:
        command.extend(["-c:a", "libmp3lame", "-q:a", "2"])
    command.append(str(dst))
    _run(command)
    report = probe(dst)
    return {
        "source": str(src),
        "destination": str(dst),
        "duration_seconds": report["duration_seconds"],
        "sample_rate": report["sample_rate"],
        "channels": report["channels"],
        "size_bytes": dst.stat().st_size,
    }


def extract_frame(
    source: str | Path, at_seconds: float, destination: str | Path
) -> dict[str, Any]:
    """Save one frame as an image an agent (or a vision model) can inspect."""
    src = _require_file(source)
    dst = _ensure_parent(destination)
    moment = max(0.0, float(at_seconds))
    if not _is_still_image(src) and probe(src)["has_video"]:
        _run(
            [
                _binary("ffmpeg"),
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                f"{moment:.3f}",
                "-i",
                str(src),
                "-frames:v",
                "1",
                str(dst),
            ]
        )
    else:
        from .image_engine import export_bytes, load_image

        dst.write_bytes(
            export_bytes(load_image(src.read_bytes()), dst.suffix.lstrip("."))
        )
    return {
        "source": str(src),
        "destination": str(dst),
        "at_seconds": round(moment, 3),
        "size_bytes": dst.stat().st_size,
    }


def contact_sheet(
    source: str | Path,
    destination: str | Path,
    *,
    count: int = 9,
    columns: int = 3,
    cell_width: int = 320,
) -> dict[str, Any]:
    """One image holding ``count`` evenly spaced frames, with their timestamps."""
    from .image_engine import load_image

    src = _require_file(source)
    info = probe(src)
    duration = info["duration_seconds"] or 0.0
    if duration <= 0:
        raise MediaToolError("contact sheet needs a timed video or audio file.")
    stamps = [
        round(duration * index / max(1, count + 1), 3) for index in range(1, count + 1)
    ]
    thumbs = []
    for index, stamp in enumerate(stamps):
        tmp = Path(_temp_path(f"sheet{index}", "png"))
        try:
            extract_frame(src, stamp, tmp)
            image = load_image(tmp.read_bytes()).convert("RGB")
        finally:
            tmp.unlink(missing_ok=True)
        ratio = image.height / max(1, image.width)
        thumbs.append(image.resize((cell_width, max(1, int(cell_width * ratio)))))
    if not thumbs:
        raise MediaToolError("no frames could be extracted.")
    from PIL import Image as PILImage

    rows = (len(thumbs) + columns - 1) // columns
    cell_height = max(image.height for image in thumbs)
    sheet = PILImage.new(
        "RGB", (columns * cell_width, rows * cell_height), (12, 14, 20)
    )
    for index, thumb in enumerate(thumbs):
        column = index % columns
        row = index // columns
        sheet.paste(thumb, (column * cell_width, row * cell_height))
    dst = _ensure_parent(destination)
    from .image_engine import export_bytes

    dst.write_bytes(export_bytes(sheet, dst.suffix.lstrip(".") or "png"))
    return {
        "source": str(src),
        "destination": str(dst),
        "frames": count,
        "columns": columns,
        "timestamps": stamps,
        "size_bytes": dst.stat().st_size,
    }


# ---------------------------------------------------------------------------
# Music editing
# ---------------------------------------------------------------------------


def trim_audio(
    source: str | Path,
    start_seconds: float,
    end_seconds: float,
    destination: str | Path,
) -> dict[str, Any]:
    """Trim an audio file to a range (re-encoded, sample accurate)."""
    return cut(source, start_seconds, end_seconds, destination, copy=False)


def fade_audio(
    source: str | Path,
    destination: str | Path,
    *,
    fade_in_seconds: float = 0.0,
    fade_out_seconds: float = 0.0,
) -> dict[str, Any]:
    """Apply fade in/out to an audio file (or a video's soundtrack)."""
    src = _require_file(source)
    dst = _ensure_parent(destination)
    info = probe(src)
    duration = info["duration_seconds"] or 0.0
    filters: list[str] = []
    if fade_in_seconds > 0:
        filters.append(f"afade=t=in:st=0:d={min(fade_in_seconds, duration):.3f}")
    if fade_out_seconds > 0:
        start = max(0.0, duration - fade_out_seconds)
        filters.append(
            f"afade=t=out:st={start:.3f}:d={min(fade_out_seconds, duration):.3f}"
        )
    if not filters:
        filters.append("anull")
    _run(
        [
            _binary("ffmpeg"),
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(src),
            "-af",
            ",".join(filters),
            *(_reencode_args(dst.suffix)),
            str(dst),
        ]
    )
    return {
        "source": str(src),
        "destination": str(dst),
        "fade_in_seconds": round(fade_in_seconds, 3),
        "fade_out_seconds": round(fade_out_seconds, 3),
        "duration_seconds": probe(dst)["duration_seconds"],
        "size_bytes": dst.stat().st_size,
    }


def loop_audio(
    source: str | Path, destination: str | Path, duration_seconds: float
) -> dict[str, Any]:
    """Loop a music bed until it reaches ``duration_seconds``."""
    src = _require_file(source)
    dst = _ensure_parent(destination)
    target = max(0.5, float(duration_seconds))
    _run(
        [
            _binary("ffmpeg"),
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-stream_loop",
            "-1",
            "-i",
            str(src),
            "-t",
            f"{target:.3f}",
            *(_reencode_args(dst.suffix)),
            str(dst),
        ]
    )
    return {
        "source": str(src),
        "destination": str(dst),
        "duration_seconds": probe(dst)["duration_seconds"],
        "size_bytes": dst.stat().st_size,
    }


def normalize_loudness(
    source: str | Path,
    destination: str | Path,
    *,
    target_lufs: float = -14.0,
    true_peak_db: float = -1.5,
) -> dict[str, Any]:
    """Loudness-normalise to a streaming target, reporting before and after."""
    src = _require_file(source)
    dst = _ensure_parent(destination)
    before = loudness(src, target_lufs=target_lufs)
    _run(
        [
            _binary("ffmpeg"),
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(src),
            "-af",
            f"loudnorm=I={target_lufs}:TP={true_peak_db}:LRA=11",
            *(_reencode_args(dst.suffix)),
            str(dst),
        ]
    )
    return {
        "source": str(src),
        "destination": str(dst),
        "before_lufs": before["integrated_lufs"],
        "after_lufs": loudness(dst, target_lufs=target_lufs)["integrated_lufs"],
        "target_lufs": target_lufs,
        "size_bytes": dst.stat().st_size,
    }


def tempo_shift(
    source: str | Path, destination: str | Path, factor: float
) -> dict[str, Any]:
    """Speed a track up or down without changing pitch (0.5x .. 2x per step)."""
    src = _require_file(source)
    dst = _ensure_parent(destination)
    speed = max(0.25, min(4.0, float(factor)))
    filters: list[str] = []
    remaining = speed
    while remaining > 2.0:
        filters.append("atempo=2.0")
        remaining /= 2.0
    while remaining < 0.5:
        filters.append("atempo=0.5")
        remaining /= 0.5
    filters.append(f"atempo={remaining:.4f}")
    _run(
        [
            _binary("ffmpeg"),
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(src),
            "-af",
            ",".join(filters),
            *(_reencode_args(dst.suffix)),
            str(dst),
        ]
    )
    return {
        "source": str(src),
        "destination": str(dst),
        "factor": round(speed, 3),
        "filter": ",".join(filters),
        "duration_seconds": probe(dst)["duration_seconds"],
        "size_bytes": dst.stat().st_size,
    }


def mix_tracks(
    tracks: list[dict[str, Any]],
    destination: str | Path,
    *,
    duration_seconds: float | None = None,
    duck: bool = True,
    duck_db: float = -12.0,
) -> dict[str, Any]:
    """Mix any number of audio tracks with per-track gain, delay and looping.

    Each track is ``{"path": ..., "gain_db": 0, "offset_seconds": 0, "loop":
    bool, "role": "voice"|"music"}``. When ``duck`` is set and one track is
    marked ``voice``, the music bus is sidechain-compressed under it — the same
    trick a podcast editor uses to keep narration on top of a bed.
    """
    if not tracks:
        raise MediaToolError("mix_tracks needs at least one track.")
    dst = _ensure_parent(destination)
    command = [_binary("ffmpeg"), "-y", "-hide_banner", "-loglevel", "error"]
    filters: list[str] = []
    labels: list[str] = []
    voice_label: str | None = None
    for index, track in enumerate(tracks):
        path = _require_file(track["path"])
        if track.get("loop"):
            command.extend(["-stream_loop", "-1"])
        command.extend(["-i", str(path)])
        steps: list[str] = []
        gain = float(track.get("gain_db", 0.0) or 0.0)
        if gain:
            steps.append(f"volume={gain}dB")
        offset = float(track.get("offset_seconds", 0.0) or 0.0)
        if offset > 0:
            steps.append(f"adelay={int(offset * 1000)}:all=1")
        label = f"t{index}"
        filters.append(
            f"[{index}:a]" + (",".join(steps) if steps else "anull") + f"[{label}]"
        )
        if str(track.get("role", "")).lower() == "voice" and voice_label is None:
            voice_label = label
        labels.append(label)
    ducked = duck and voice_label is not None and len(labels) > 1
    if ducked and voice_label is not None:
        # Music bus first, then a sidechain compressor driven by the voice.
        music = [label for label in labels if label != voice_label]
        filters.append(
            "".join(f"[{label}]" for label in music)
            + f"amix=inputs={len(music)}:normalize=0[musicbus]"
        )
        filters.append(
            f"[musicbus][{voice_label}]sidechaincompress="
            "threshold=0.05:ratio=12:attack=20:release=300[ducked]"
        )
        filters.append(
            f"[ducked][{voice_label}]amix=inputs=2:normalize=0,"
            f"volume={max(0.0, 1.0 + duck_db / 40):.3f}[out]"
        )
    else:
        filters.append(
            "".join(f"[{label}]" for label in labels)
            + f"amix=inputs={len(labels)}:normalize=0[out]"
        )
    if duration_seconds:
        # Pad the mix so a requested length is always honoured (the voice bus
        # usually ends before the music bed does).
        filters[-1] = filters[-1].replace("[out]", ",apad[out]")
    command.extend(["-filter_complex", ";".join(filters), "-map", "[out]"])
    if duration_seconds:
        command.extend(["-t", f"{max(0.5, float(duration_seconds)):.3f}"])
    command.extend(_reencode_args(dst.suffix))
    command.append(str(dst))
    _run(command)
    return {
        "destination": str(dst),
        "track_count": len(tracks),
        "tracks": [
            {
                "path": str(track["path"]),
                "gain_db": float(track.get("gain_db", 0.0) or 0.0),
                "offset_seconds": float(track.get("offset_seconds", 0.0) or 0.0),
                "loop": bool(track.get("loop")),
                "role": track.get("role"),
            }
            for track in tracks
        ],
        "ducked": ducked,
        "duration_seconds": probe(dst)["duration_seconds"],
        "loudness": loudness(dst)["integrated_lufs"],
        "size_bytes": dst.stat().st_size,
    }


# ---------------------------------------------------------------------------
# Image composition
# ---------------------------------------------------------------------------

_BLEND_MODES: dict[str, Any] = {}


def _blend(name: str) -> Any:
    from PIL import ImageChops

    if not _BLEND_MODES:
        _BLEND_MODES.update(
            {
                "normal": None,
                "multiply": ImageChops.multiply,
                "screen": ImageChops.screen,
                "add": ImageChops.add,
                "difference": ImageChops.difference,
                "overlay": ImageChops.overlay,
                "hard_light": ImageChops.hard_light,
                "soft_light": ImageChops.soft_light,
            }
        )
    mode = str(name or "normal").lower()
    if mode not in _BLEND_MODES:
        raise MediaToolError(
            f"Unknown blend mode '{name}'. Known: {sorted(_BLEND_MODES)}"
        )
    return _BLEND_MODES[mode]


def compose_layers(
    base: str | Path,
    layers: list[dict[str, Any]],
    destination: str | Path,
) -> dict[str, Any]:
    """Composite images on top of each other — the "ghép ảnh" operator.

    A layer is ``{"path": ..., "x": 0, "y": 0, "scale": 1.0, "opacity": 1.0,
    "rotate": 0, "blend": "normal"}``. ``x``/``y`` accept an int (pixels) or a
    string anchor such as ``"center"``, ``"top-right"``, ``"bottom-left"``.
    """
    from PIL import Image as PILImage

    from .image_engine import export_bytes, load_image

    base_path = _require_file(base)
    canvas = load_image(base_path.read_bytes()).convert("RGBA")
    applied: list[dict[str, Any]] = []
    for index, layer in enumerate(layers):
        layer_path = _require_file(layer["path"])
        image = load_image(layer_path.read_bytes()).convert("RGBA")
        scale = float(layer.get("scale", 1.0) or 1.0)
        if scale != 1.0:
            size = (
                max(1, int(image.width * scale)),
                max(1, int(image.height * scale)),
            )
            image = image.resize(size, PILImage.Resampling.LANCZOS)
        rotate = float(layer.get("rotate", 0.0) or 0.0)
        if rotate:
            image = image.rotate(rotate, expand=True)
        opacity = float(layer.get("opacity", 1.0) or 1.0)
        if opacity < 1.0:
            factor = max(0.0, opacity)
            image.putalpha(
                image.getchannel("A").point(
                    [int(value * factor) for value in range(256)]
                )
            )
        position = _anchor(layer.get("x", 0), layer.get("y", 0), image, canvas)
        blend = _blend(layer.get("blend", "normal"))
        if blend is None:
            canvas.alpha_composite(image, dest=position)
        else:
            region = canvas.crop(
                (
                    position[0],
                    position[1],
                    position[0] + image.width,
                    position[1] + image.height,
                )
            )
            blended = blend(region.convert("RGB"), image.convert("RGB")).convert("RGBA")
            canvas.paste(blended, position, image.getchannel("A"))
        applied.append(
            {
                "index": index,
                "path": str(layer_path),
                "position": [position[0], position[1]],
                "scale": scale,
                "opacity": opacity,
                "rotate": rotate,
                "blend": str(layer.get("blend", "normal")),
            }
        )
    dst = _ensure_parent(destination)
    dst.write_bytes(export_bytes(canvas, dst.suffix.lstrip(".") or "png"))
    return {
        "base": str(base_path),
        "destination": str(dst),
        "width": canvas.width,
        "height": canvas.height,
        "layer_count": len(applied),
        "layers": applied,
        "size_bytes": dst.stat().st_size,
    }


_ANCHOR_WORDS: dict[str, tuple[str, str]] = {
    "top-left": ("left", "top"),
    "top-right": ("right", "top"),
    "top-center": ("center", "top"),
    "bottom-left": ("left", "bottom"),
    "bottom-right": ("right", "bottom"),
    "bottom-center": ("center", "bottom"),
    "center-left": ("left", "center"),
    "center-right": ("right", "center"),
    "center": ("center", "center"),
    "middle": ("center", "center"),
}


def _anchor(x: Any, y: Any, image: Any, canvas: Any) -> tuple[int, int]:
    """Resolve ``x``/``y`` to a position.

    Accepts pixels, percentages (``"50%"``), single anchors (``"center"``,
    ``"top"``) and corner anchors (``"bottom-right"``), which is how a text-only
    agent naturally talks about placement.
    """
    horizontal, vertical = x, y
    if isinstance(x, str):
        key = x.strip().lower().replace("_", "-")
        if "-" in key and key not in _ANCHOR_WORDS:
            head, _, tail = key.partition("-")
            for word in (head, tail):
                if word in {"left", "right"}:
                    horizontal = word
                if word in {"top", "bottom"}:
                    vertical = word
        elif key in _ANCHOR_WORDS:
            horizontal, vertical = _ANCHOR_WORDS[key]
    if isinstance(y, str) and y.strip().lower().replace("_", "-") in _ANCHOR_WORDS:
        _, vertical = _ANCHOR_WORDS[y.strip().lower().replace("_", "-")]
    return (
        _axis(horizontal, image.width, canvas.width, "left"),
        _axis(vertical, image.height, canvas.height, "top"),
    )


def _axis(value: Any, item: int, container: int, default: str) -> int:
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"left", "top", "start"}:
            return 0
        if text in {"center", "middle"}:
            return (container - item) // 2
        if text in {"right", "bottom", "end"}:
            return container - item
        if text.endswith("%"):
            try:
                return int((container - item) * float(text[:-1]) / 100.0)
            except ValueError as exc:
                raise MediaToolError(f"'{value}' is not a valid position.") from exc
        try:
            return int(text)
        except ValueError as exc:
            raise MediaToolError(f"'{value}' is not a valid position.") from exc
    if value is None:
        return 0 if default in {"left", "top"} else (container - item) // 2
    return int(value)


def collage(
    sources: Sequence[str | Path],
    destination: str | Path,
    *,
    columns: int = 2,
    cell_width: int = 720,
    gap: int = 8,
    background: str = "#0c0e14",
    captions: list[str] | None = None,
) -> dict[str, Any]:
    """Grid several images into one sheet, with optional captions per cell."""
    from PIL import Image as PILImage
    from PIL import ImageDraw

    from .image_engine import export_bytes, load_image

    if not sources:
        raise MediaToolError("collage needs at least one image.")
    cells = []
    for path in sources:
        resolved = _require_file(path)
        image = load_image(resolved.read_bytes()).convert("RGB")
        ratio = image.height / max(1, image.width)
        cells.append(image.resize((cell_width, max(1, int(cell_width * ratio)))))
    columns = max(1, min(columns, len(cells)))
    rows = (len(cells) + columns - 1) // columns
    cell_height = max(image.height for image in cells)
    caption_band = 28 if captions else 0
    sheet = PILImage.new(
        "RGB",
        (
            columns * cell_width + gap * (columns + 1),
            rows * (cell_height + caption_band) + gap * (rows + 1),
        ),
        background,
    )
    draw = ImageDraw.Draw(sheet)
    mapping: list[dict[str, Any]] = []
    for index, cell in enumerate(cells):
        column = index % columns
        row = index // columns
        x = gap + column * (cell_width + gap)
        y = gap + row * (cell_height + caption_band + gap)
        sheet.paste(cell, (x, y))
        if captions and index < len(captions):
            draw.text(
                (x + 4, y + cell.height + 6), str(captions[index]), fill="#e6e8ee"
            )
        mapping.append(
            {
                "index": index,
                "column": column,
                "row": row,
                "box": [x, y, x + cell.width, y + cell.height],
                "caption": captions[index]
                if captions and index < len(captions)
                else None,
            }
        )
    dst = _ensure_parent(destination)
    dst.write_bytes(export_bytes(sheet, dst.suffix.lstrip(".") or "png"))
    return {
        "destination": str(dst),
        "count": len(cells),
        "columns": columns,
        "rows": rows,
        "width": sheet.width,
        "height": sheet.height,
        "cells": mapping,
        "size_bytes": dst.stat().st_size,
    }
