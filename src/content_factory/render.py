"""Small ffmpeg renderer for the server-side timeline export path.

Supports three layers per scene:
  * a visual base — a source image/video (``image_url``) when available,
    otherwise a colour card;
  * narration text drawn over the visual;
  * audio — per-scene voiceover (``narration_url``) and an optional background
    music bed, mixed together.

Narration text is written to a temporary ``textfile`` and referenced with
``textfile=`` rather than inline ``text=``. Inline text is fragile: an
apostrophe or other character inside ``text='...'`` confuses ffmpeg's filter
parser and aborts the whole render with "Option not found". A ``textfile``
sidesteps every escaping problem for arbitrary narration.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path

from .models import RenderPlan
from .resources import ResourceGovernor, default_governor

#: Callable that resolves a media URL (image_url / narration_url) to a local
#: file path, or None when the URL is not resolvable locally.
MediaResolver = Callable[[str], Path | None]


class RenderError(RuntimeError):
    """Raised when ffmpeg cannot produce the requested video."""


_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff"}


def render_video_file(
    plan: RenderPlan,
    output_path: Path,
    *,
    ffmpeg_binary: str | None = None,
    resolve_media: MediaResolver | None = None,
    music_path: Path | None = None,
    background_video: Path | None = None,
    export_format: str = "webm",
    threads: int = 1,
    audio_path: Path | None = None,
    governor: ResourceGovernor | None = None,
) -> Path:
    """Render a plan to a real WebM (VP9) with visuals + voiceover + music.

    ``resolve_media`` maps a scene's ``image_url``/``narration_url`` to a local
    file so the renderer can composite real footage and mix the narration.
    ``music_path`` is an optional background-music file played under the
    voiceover at the volume declared on the plan's music track.
    ``background_video``, when given, is a source video used as a continuously
    moving backdrop (looped to the plan's total length) with each scene's
    narration text overlaid at its own time window — real footage, not cards.
    """
    if export_format not in {"webm", "mp4"}:
        raise RenderError("export_format must be webm or mp4.")
    if type(threads) is not int or not 1 <= threads <= 8:
        raise RenderError("threads must be an integer between 1 and 8.")
    plan = plan.model_copy(deep=True)
    if audio_path is not None:
        for step in plan.steps:
            step.narration_url = None
        plan.audio = []
        music_path = audio_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output_path.parent, prefix=".render-") as tmp:
        target = Path(tmp) / f"video.{export_format}"
        if background_video is not None and not any(s.image_url for s in plan.steps):
            _render_with_background_video(
                plan,
                target,
                background_video,
                ffmpeg_binary=ffmpeg_binary,
                resolve_media=resolve_media,
                music_path=music_path,
                export_format=export_format,
                threads=threads,
                finished_mix=audio_path is not None,
                governor=governor,
            )
        else:
            _render_scenes(
                plan,
                target,
                ffmpeg_binary=ffmpeg_binary,
                resolve_media=resolve_media,
                music_path=music_path,
                background_video=background_video,
                export_format=export_format,
                threads=threads,
                finished_mix=audio_path is not None,
                governor=governor,
            )
        target.replace(output_path)
    return output_path


def _render_scenes(
    plan: RenderPlan,
    output_path: Path,
    *,
    ffmpeg_binary: str | None,
    resolve_media: MediaResolver | None,
    music_path: Path | None,
    export_format: str,
    threads: int,
    finished_mix: bool,
    background_video: Path | None = None,
    governor: ResourceGovernor | None = None,
) -> Path:
    """Render the per-scene path: colour cards or per-scene images + audio."""
    import tempfile

    binary = ffmpeg_binary or shutil.which("ffmpeg")
    if binary is None:
        raise RenderError("ffmpeg is required for server-side rendering.")
    if not plan.steps:
        raise RenderError("Cannot render an empty timeline.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    font_file = _find_font()
    resolve_media = resolve_media or (lambda _url: None)
    music_volume = 1.0 if finished_mix else _music_volume(plan)

    inputs: list[str] = []
    filters: list[str] = []
    narration_labels: list[str] = []
    input_idx = 0

    with tempfile.TemporaryDirectory(prefix="cf-render-") as tmp:
        tmpdir = Path(tmp)
        for index, step in enumerate(plan.steps):
            dur = step.duration_seconds
            # --- Visual base: source media or colour card ----------------------
            src = resolve_media(step.image_url) if step.image_url else background_video
            if src is not None and src.is_file():
                is_image = src.suffix.lower() in _IMAGE_EXTS
                if is_image:
                    inputs += ["-loop", "1", "-i", str(src)]
                else:
                    inputs += ["-stream_loop", "-1", "-i", str(src)]
                vidx = input_idx
                input_idx += 1
                vchain = (
                    f"[{vidx}:v]"
                    f"scale={plan.width}:{plan.height}:force_original_aspect_ratio=increase,"
                    f"crop={plan.width}:{plan.height},setsar=1,"
                    f"trim=start={step.source_in_seconds},"
                    f"setpts=(PTS-STARTPTS)/{step.speed},fps={plan.fps},"
                    f"trim=duration={dur},setpts=PTS-STARTPTS,"
                )
            else:
                color = (
                    step.background
                    if _HEX_COLOR.fullmatch(step.background)
                    else "#111827"
                )
                inputs += [
                    "-f",
                    "lavfi",
                    "-i",
                    f"color=c={color}:s={plan.width}x{plan.height}:r={plan.fps}:"
                    f"d={dur}",
                ]
                vidx = input_idx
                input_idx += 1
                vchain = f"[{vidx}:v]"
            if font_file and step.text:
                font = _escape_filter_path(font_file)
                textfile = tmpdir / f"text_{index}.txt"
                textfile.write_text(step.text, encoding="utf-8")
                tf = _escape_filter_path(textfile)
                vchain += (
                    f"drawtext=fontfile='{font}':textfile='{tf}':"
                    f"fontcolor={step.text_color}:fontsize={step.font_size}:"
                    "x=(w-text_w)/2:y=(h-text_h)/2"
                )
            separator = "" if vchain.endswith((",", "]")) else ","
            filters.append(f"{vchain}{separator}format=yuv420p[v{index}]")

            # --- Voiceover for this scene -------------------------------------
            nar = resolve_media(step.narration_url) if step.narration_url else None
            if nar is not None and nar.is_file():
                inputs += ["-i", str(nar)]
                naidx = input_idx
                input_idx += 1
                start_ms = int(step.start_seconds * 1000)
                vol = float(step.volume) * _voice_volume(plan)
                filters.append(
                    f"[{naidx}:a]atrim=0:{dur},asetpts=PTS-STARTPTS,"
                    f"volume={vol},adelay={start_ms}:all=1[n{index}]"
                )
                narration_labels.append(f"[n{index}]")

        # --- Concatenate the video scenes -------------------------------------
        filters.append(
            f"{''.join(f'[v{index}]' for index in range(len(plan.steps)))}"
            f"concat=n={len(plan.steps)}:v=1:a=0[outv]"
        )

        # --- Background music ---------------------------------------------------
        if music_path is not None and music_path.is_file():
            inputs += ([] if finished_mix else ["-stream_loop", "-1"]) + [
                "-i",
                str(music_path),
            ]
            midx = input_idx
            input_idx += 1
            filters.append(
                f"[{midx}:a]atrim=0:{plan.total_seconds},"
                f"asetpts=PTS-STARTPTS,volume={music_volume}[m]"
            )
            narration_labels.append("[m]")

        # --- Mix the audio tracks (voiceover + music) --------------------------
        audio_args: list[str] = []
        if narration_labels:
            filters.append(
                f"{''.join(narration_labels)}"
                f"amix=inputs={len(narration_labels)}:normalize=0,"
                f"apad,atrim=0:{plan.total_seconds}[outa]"
            )
            audio_args = [
                "-map",
                "[outa]",
                "-c:a",
                "aac" if export_format == "mp4" else "libopus",
            ]

        prefix = [
            binary,
            "-y",
            "-filter_complex_threads",
            str(threads),
            "-filter_threads",
            str(threads),
            *_bounded_inputs(inputs, threads),
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[outv]",
            *audio_args,
            "-r",
            str(plan.fps),
        ]
        completed = _run_encode(
            prefix,
            export_format=export_format,
            threads=threads,
            total_seconds=plan.total_seconds,
            output_path=output_path,
            governor=governor,
        )
    if completed.returncode != 0:
        detail = completed.stderr.strip().splitlines()[-1:] or ["unknown ffmpeg error"]
        raise RenderError(detail[0])
    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise RenderError("ffmpeg finished without creating a video file.")
    return output_path


def _render_with_background_video(
    plan: RenderPlan,
    output_path: Path,
    background_video: Path,
    *,
    ffmpeg_binary: str | None,
    resolve_media: MediaResolver | None,
    music_path: Path | None,
    export_format: str,
    threads: int,
    finished_mix: bool,
    governor: ResourceGovernor | None = None,
) -> Path:
    """Render using a source video as a moving backdrop + text + voiceover + music.

    The source video is looped to the plan's total length, scaled/cropped to the
    canvas, and each scene's narration text is overlaid at its own time window
    via ``enable='between(t,start,end)'``. Voiceover clips and the music bed are
    mixed underneath. This yields real moving footage instead of colour cards.
    """
    import tempfile

    binary = ffmpeg_binary or shutil.which("ffmpeg")
    if binary is None:
        raise RenderError("ffmpeg is required for server-side rendering.")
    if not plan.steps:
        raise RenderError("Cannot render an empty timeline.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    font_file = _find_font()
    resolve_media = resolve_media or (lambda _url: None)
    music_volume = 1.0 if finished_mix else _music_volume(plan)

    inputs: list[str] = ["-stream_loop", "-1", "-i", str(background_video)]
    filters: list[str] = []
    narration_labels: list[str] = []
    input_idx = 1  # input 0 is the background video

    with tempfile.TemporaryDirectory(prefix="cf-render-") as tmp:
        tmpdir = Path(tmp)
        # Scale/crop the looping background to the canvas.
        bg_label = (
            f"[0:v]scale={plan.width}:{plan.height}:force_original_aspect_ratio=increase,"
            f"crop={plan.width}:{plan.height},setsar=1,fps={plan.fps},"
            f"trim=duration={plan.total_seconds},setpts=PTS-STARTPTS[bg]"
        )
        prev = "[bg]"
        for index, step in enumerate(plan.steps):
            if font_file and step.text:
                font = _escape_filter_path(font_file)
                textfile = tmpdir / f"text_{index}.txt"
                textfile.write_text(step.text, encoding="utf-8")
                tf = _escape_filter_path(textfile)
                enable = (
                    f"enable='between(t,{step.start_seconds:.2f},"
                    f"{step.end_seconds:.2f})'"
                )
                label = f"t{index}"
                filters.append(
                    f"{prev}drawtext=fontfile='{font}':textfile='{tf}':"
                    f"fontcolor={step.text_color}:fontsize={step.font_size}:"
                    f"x=(w-text_w)/2:y=(h-text_h)/2:{enable}[{label}]"
                )
                prev = f"[{label}]"
            # Voiceover for this scene.
            nar = resolve_media(step.narration_url) if step.narration_url else None
            if nar is not None and nar.is_file():
                inputs += ["-i", str(nar)]
                naidx = input_idx
                input_idx += 1
                start_ms = int(step.start_seconds * 1000)
                vol = float(step.volume) * _voice_volume(plan)
                filters.append(
                    f"[{naidx}:a]atrim=0:{step.duration_seconds},"
                    f"asetpts=PTS-STARTPTS,volume={vol},"
                    f"adelay={start_ms}:all=1[n{index}]"
                )
                narration_labels.append(f"[n{index}]")

        filters.insert(0, bg_label)
        filters.append(f"{prev}format=yuv420p[outv]")

        # Background music.
        if music_path is not None and music_path.is_file():
            inputs += ([] if finished_mix else ["-stream_loop", "-1"]) + [
                "-i",
                str(music_path),
            ]
            midx = input_idx
            input_idx += 1
            filters.append(
                f"[{midx}:a]atrim=0:{plan.total_seconds},"
                f"asetpts=PTS-STARTPTS,volume={music_volume}[m]"
            )
            narration_labels.append("[m]")

        audio_args: list[str] = []
        if narration_labels:
            filters.append(
                f"{''.join(narration_labels)}"
                f"amix=inputs={len(narration_labels)}:normalize=0,"
                f"apad,atrim=0:{plan.total_seconds}[outa]"
            )
            audio_args = [
                "-map",
                "[outa]",
                "-c:a",
                "aac" if export_format == "mp4" else "libopus",
            ]

        prefix = [
            binary,
            "-y",
            "-filter_complex_threads",
            str(threads),
            "-filter_threads",
            str(threads),
            *_bounded_inputs(inputs, threads),
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[outv]",
            *audio_args,
            "-r",
            str(plan.fps),
        ]
        completed = _run_encode(
            prefix,
            export_format=export_format,
            threads=threads,
            total_seconds=plan.total_seconds,
            output_path=output_path,
            governor=governor,
        )
    if completed.returncode != 0:
        detail = completed.stderr.strip().splitlines()[-1:] or ["unknown ffmpeg error"]
        raise RenderError(detail[0])
    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise RenderError("ffmpeg finished without creating a video file.")
    return output_path


def _bounded_inputs(inputs: list[str], threads: int) -> list[str]:
    result: list[str] = []
    for value in inputs:
        if value == "-i":
            result += ["-threads", str(threads), "-protocol_whitelist", "file,pipe"]
        result.append(value)
    return result


def _run_command(
    command: list[str], timeout: float
) -> subprocess.CompletedProcess[str]:
    """Run ffmpeg with a hard deadline; a hung encoder must not pin the machine."""
    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise RenderError(
            f"ffmpeg exceeded the {timeout:.0f}s render budget and was killed to "
            "protect the machine; raise CONTENT_FACTORY_RENDER_TIMEOUT_SECONDS "
            "for very long timelines."
        ) from exc


def _run_encode(
    prefix: list[str],
    *,
    export_format: str,
    threads: int,
    total_seconds: float,
    output_path: Path,
    governor: ResourceGovernor | None,
) -> subprocess.CompletedProcess[str]:
    """Encode with the best available device, and fall back instead of failing.

    The encoder is chosen by the resource governor: a hardware encoder when this
    machine exposes one and the policy allows it, the software encoder otherwise.
    If a hardware encoder fails at runtime (driver reset, another process holding
    the encoder session, VRAM exhausted), the export is retried once in software
    so a GPU problem never costs the whole job.
    """
    resolved = governor or default_governor()
    choice = resolved.video_codec(export_format)
    command = [
        *prefix,
        *choice.args,
        "-threads",
        str(threads),
        "-t",
        str(total_seconds),
        str(output_path),
    ]
    completed = _run_command(command, resolved.settings.render_timeout_seconds)
    resolved.note_encoder(choice.encoder)
    if completed.returncode == 0 or not choice.hardware:
        return completed
    resolved.note_encoder_fallback(choice.encoder)
    software = resolved.software_video_codec(export_format)
    retry = [
        *prefix,
        *software.args,
        "-threads",
        str(threads),
        "-t",
        str(total_seconds),
        str(output_path),
    ]
    return _run_command(retry, resolved.settings.render_timeout_seconds)


def _voice_volume(plan: RenderPlan) -> float:
    for track in plan.audio:
        if track.kind == "voiceover":
            return float(track.volume) if track.enabled else 0.0
    return 1.0


def _music_volume(plan: RenderPlan) -> float:
    """Pick the music-track volume from the plan (defaults to a quiet bed)."""
    for track in plan.audio:
        if track.kind == "music":
            return float(track.volume) if track.enabled else 0.0
    return 0.25


def _escape_drawtext(value: str) -> str:
    """Escape text for ffmpeg's drawtext filter syntax."""
    compact = " ".join((value or "").split())
    return (
        compact.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace("%", "\\%")
    )


def _escape_filter_path(path: Path) -> str:
    """Escape a filesystem path for an ffmpeg filter option."""
    return _escape_drawtext(str(path).replace("\\", "/"))


def _find_font() -> Path | None:
    """Find a portable font without relying on Fontconfig defaults."""
    candidates = (
        (Path(os.environ["WINDIR"]) / "Fonts" / "arial.ttf")
        if "WINDIR" in os.environ
        else Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/segoeui.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    )
    return next((candidate for candidate in candidates if candidate.is_file()), None)
