"""Media tool engine: everything an agent needs to *read* and *cut* media.

The whole point of this module is that a text-only model — no vision, no
ears — can operate on real media. So every operation here has two halves:

* a **reading** half that turns a file into structured text the agent can
  reason about (duration, streams, loudness, silence, scene cuts, palette,
  beat grid), now living in :mod:`content_factory.media_probe`; and
* a **cutting/composing** half — this module — that turns an agent's decision
  back into a new file (trim, split, concat, extract, fade, loop,
  loudness-normalise, mix tracks, compose image layers, collage).

The reading names are still importable from here: this module re-exports them
so existing callers (``from .media_tools import probe``) keep working without
knowing the split happened.

Nothing here knows about projects or the service layer; it is pure media I/O
over ``ffmpeg``/``ffprobe`` plus Pillow, which keeps it hermetic and testable.
"""

from __future__ import annotations

import itertools
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .media_probe import (
    DESCRIBE_SECTIONS,
    MediaToolArgumentError,
    MediaToolError,
    _binary,
    _ensure_parent,
    _require_file,
    _run,
    _temp_path,
    beat_grid,
    describe,
    extract_frame,
    loudness,
    palette,
    probe,
    scene_cuts,
    silence_ranges,
)

__all__ = [
    "DESCRIBE_SECTIONS",
    "MediaToolArgumentError",
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
    for index, (start, end) in enumerate(itertools.pairwise(bounds)):
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
