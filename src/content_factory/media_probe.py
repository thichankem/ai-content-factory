"""Media *reading* engine: turn a file into structured text an agent can reason on.

The reading half of :mod:`content_factory.media_tools`, split out so the module
that *writes* media (``media_tools``) can stay focused on cutting, mixing and
compositing.  It also owns the ffmpeg/ffprobe process plumbing every media
operation needs — the binary lookup, the failure classifier and the temp-file
helper — because both halves depend on it and it must live below them.

Nothing here knows about projects or the service layer; it is pure media I/O
over ``ffmpeg``/``ffprobe`` plus Pillow, which keeps it hermetic and testable.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import numpy as np

from .hardware import require_ffmpeg, resolve_ffprobe
from .resources import Admission, JobKind, ResourceGovernor, default_governor

__all__ = [
    "DESCRIBE_SECTIONS",
    "MediaToolArgumentError",
    "MediaToolError",
    "beat_grid",
    "describe",
    "extract_frame",
    "loudness",
    "palette",
    "probe",
    "scene_cuts",
    "silence_ranges",
]


class MediaToolError(RuntimeError):
    """Raised when a media operation cannot be completed."""


class MediaToolArgumentError(MediaToolError):
    """Raised when the *caller* passed something the tool cannot accept.

    A subclass of :class:`MediaToolError` so existing ``except MediaToolError``
    code keeps working, but distinct so the HTTP layer can answer 422 ("fix
    your request") rather than 500 ("the server broke") — the two used to be
    indistinguishable to a client, and only one of them is retryable.
    """


#: Sections :func:`describe` can build; anything else is a typo worth naming.
DESCRIBE_SECTIONS = ("loudness", "silence", "cuts", "palette", "beats", "text")


# ---------------------------------------------------------------------------
# Process helpers
# ---------------------------------------------------------------------------


def _binary(name: str) -> str:
    """Resolve an external tool, with the same fallbacks the app uses.

    ``ffmpeg`` resolves through :func:`hardware.require_ffmpeg`, so an install
    that only ships the ``imageio-ffmpeg`` build still works without a system
    install — the promise the docs make, which this module used to break by
    consulting ``PATH`` alone. ``ffprobe`` resolves from ``PATH`` or beside
    that ffmpeg; :func:`_probe_json` degrades to ffmpeg's own metadata when the
    machine genuinely has none. Any other tool must be on ``PATH``.
    """
    if name == "ffmpeg":
        return require_ffmpeg(purpose="media tools", error=MediaToolError)
    if name == "ffprobe":
        found = resolve_ffprobe()
        if found is None:
            raise MediaToolError("ffprobe is not available on this machine.")
        return found
    path = shutil.which(name)
    if path is None:
        raise MediaToolError(f"'{name}' is required but was not found on PATH.")
    return path


#: ffmpeg's wording when the *input* is the problem rather than the server.
#: These are the caller's to fix (a corrupt file, an HTML page named .mp4, a
#: container ffmpeg cannot open), so they answer 422; everything else — a
#: missing binary, a broken filter — stays a 500, because retrying the request
#: as written would not help.
_INPUT_FAILURE_MARKERS = (
    "invalid data found",
    "moov atom not found",
    "could not find codec parameters",
    "no such file",
    "error opening input",
    "end of file",
    "not a valid",
)


def _ffmpeg_error(detail: str, fallback: str) -> MediaToolError:
    """Classify an ffmpeg/ffprobe failure: unreadable input, or a broken tool."""
    message = detail or fallback
    lowered = message.lower()
    if any(marker in lowered for marker in _INPUT_FAILURE_MARKERS):
        return MediaToolArgumentError(f"cannot read this media file: {message}")
    return MediaToolError(message)


def _run(command: list[str]) -> subprocess.CompletedProcess[bytes]:
    proc = subprocess.run(command, capture_output=True, check=False)
    if proc.returncode != 0:
        lines = proc.stderr.decode("utf-8", "replace").strip().splitlines()
        raise _ffmpeg_error(lines[-1] if lines else "", f"{command[0]} failed")
    return proc


def _require_file(path: str | Path) -> Path:
    resolved = Path(path)
    if not resolved.is_file():
        # The caller named a file that is not there: a request problem, not a
        # server one. ``MediaToolArgumentError`` answers 422 with the path.
        raise MediaToolArgumentError(f"media file not found: '{resolved}'")
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


def _temp_path(stem: str, suffix: str) -> str:
    """Reserve a unique temp path that is free for ffmpeg/Pillow to write."""
    import os
    import tempfile

    handle, name = tempfile.mkstemp(prefix=f"{stem}-", suffix=f".{suffix}")
    os.close(handle)
    Path(name).unlink(missing_ok=True)
    return name


# ---------------------------------------------------------------------------
# Reading: probe + loudness + silence + cuts + palette
# ---------------------------------------------------------------------------


_FFMPEG_INPUT_RE = re.compile(r"Input #0,\s*(.+?),\s*from")
_FFMPEG_DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)")
_FFMPEG_BITRATE_RE = re.compile(r"bitrate:\s*(\d+(?:\.\d+)?)\s*kb/s")
_FFMPEG_SIZE_RE = re.compile(r"[,\s](\d{1,5})x(\d{1,5})[,\s\[]")
_FFMPEG_FPS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*fps")
_FFMPEG_RATE_RE = re.compile(r"(\d+)\s*Hz")


def _stream_codec(line: str, marker: str) -> str | None:
    """The codec name in a ``Stream`` line, e.g. ``h264`` from ``Video: h264``."""
    rest = line.split(marker, 1)[1].strip()
    token = re.split(r"[\s,(]", rest, maxsplit=1)[0]
    return token or None


def _probe_json_from_ffmpeg(path: Path) -> dict[str, Any]:
    """Probe with ffmpeg alone, for machines that ship no ffprobe.

    ``imageio-ffmpeg`` bundles ``ffmpeg`` but not ``ffprobe``, so "install
    imageio-ffmpeg and every media feature works" only held for the tools that
    re-encode — anything that *reads* a file still refused to run. ``ffmpeg
    -i`` prints the same container and stream facts (before exiting non-zero
    with no output), so they are parsed back into ffprobe's shape here.
    """
    proc = subprocess.run(
        [_binary("ffmpeg"), "-hide_banner", "-i", str(path)],
        capture_output=True,
        check=False,
    )
    text = proc.stderr.decode("utf-8", "replace")
    streams: list[dict[str, Any]] = []
    for line in text.splitlines():
        if "Stream #" not in line:
            continue
        if " Video: " in line:
            video: dict[str, Any] = {
                "codec_type": "video",
                "codec_name": _stream_codec(line, "Video: "),
            }
            size = _FFMPEG_SIZE_RE.search(line)
            if size:
                video["width"] = int(size.group(1))
                video["height"] = int(size.group(2))
            fps = _FFMPEG_FPS_RE.search(line)
            if fps:
                video["avg_frame_rate"] = f"{round(float(fps.group(1)))}/1"
            streams.append(video)
        elif " Audio: " in line:
            audio: dict[str, Any] = {
                "codec_type": "audio",
                "codec_name": _stream_codec(line, "Audio: "),
            }
            rate = _FFMPEG_RATE_RE.search(line)
            if rate:
                audio["sample_rate"] = rate.group(1)
            lowered = line.lower()
            if "mono" in lowered:
                audio["channels"] = 1
            elif "stereo" in lowered:
                audio["channels"] = 2
            streams.append(audio)
    fmt: dict[str, Any] = {}
    name = _FFMPEG_INPUT_RE.search(text)
    if name:
        fmt["format_name"] = name.group(1).strip()
    duration = _FFMPEG_DURATION_RE.search(text)
    if duration:
        hours, minutes, seconds = (float(part) for part in duration.groups())
        fmt["duration"] = round(hours * 3600 + minutes * 60 + seconds, 3)
    bitrate = _FFMPEG_BITRATE_RE.search(text)
    if bitrate:
        fmt["bit_rate"] = int(float(bitrate.group(1)) * 1000)
    if not streams and not fmt:
        lines = text.strip().splitlines()
        raise _ffmpeg_error(
            lines[-1] if lines else "", "ffmpeg could not read this file"
        )
    return {"streams": streams, "format": fmt}


def _probe_json(path: Path) -> dict[str, Any]:
    ffprobe = resolve_ffprobe()
    if ffprobe is None:
        return _probe_json_from_ffmpeg(path)
    proc = _run(
        [
            ffprobe,
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
        "streams_known": bool(streams),
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


def _energy_envelope(
    path: Path, *, frame_seconds: float = 0.02
) -> tuple[np.ndarray, float]:
    """Short-window RMS envelope used for beat picking (pure numpy)."""
    from .perception import _decode_mono_pcm

    samples, rate = _decode_mono_pcm(path)
    if len(samples) == 0:
        return np.zeros(0, dtype=np.float32), 0.0
    hop = max(1, round(frame_seconds * rate))
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
        search = max(1, round(0.35 * interval / frame_seconds))
        index = 0
        while index * frame_seconds < duration and len(beats) < max_beats:
            centre = round(index * interval / frame_seconds)
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


def describe(
    path: str | Path,
    *,
    include: list[str] | None = None,
    governor: ResourceGovernor | None = None,
) -> dict[str, Any]:
    """Everything a text-only agent needs to reason about a media file.

    One call answers: how long is it, what is in it, how loud is it, where are
    the silences, where are the shot changes, what is the colour palette, and
    what is the tempo. Optional sections (``include``) cover the slower passes
    (``cuts``, ``palette``, ``beats``, ``loudness``, ``silence``, ``text``).
    """
    resolved = _require_file(path)
    unknown = sorted(set(include or ()) - set(DESCRIBE_SECTIONS))
    if unknown:
        msg = (
            f"Unknown describe section(s) {unknown}; valid sections are "
            f"{list(DESCRIBE_SECTIONS)}."
        )
        raise MediaToolArgumentError(msg)
    wanted = set(include or DESCRIBE_SECTIONS)
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
        report["text"] = ocr_text(resolved, governor=governor)
    return report


def ocr_text(
    path: str | Path, *, governor: ResourceGovernor | None = None
) -> dict[str, Any]:
    """Read words out of an image/video frame using ``tesseract`` or ``easyocr``.

    The local model runs through the resource governor, so a read never starts
    while another heavy job owns the machine, and the GPU is used only when the
    installed torch build can actually see it.
    """
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

        resolved_governor = governor or default_governor()
        with resolved_governor.job(JobKind.OCR) as decision:
            on_gpu = decision.admission is Admission.GPU
            reader = easyocr.Reader(["en"], gpu=on_gpu, verbose=False)
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
            "device": "cuda" if on_gpu else "cpu",
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
