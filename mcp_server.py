"""MCP server for the AI Content Factory media, edit, voice, and vision tools.

Exposes the universal media library (upload / list / transcribe), the content
re-cook pipeline, and a set of media-editing, voice, and (optional) vision
tools as Model Context Protocol tools, so any MCP-capable AI agent (Claude,
Codex, Gemini, ...) can ingest media, read it, edit it, and spin up projects.

Every file read or write is confined to the configured asset directories by a
:class:`Sandbox` — an agent can never touch files outside ``media_dir``,
``uploads_dir``, ``cache_dir``, and ``library_dir``.

Run::

    python mcp_server.py          # stdio transport (default)
    python mcp_server.py --sse    # SSE transport on :8765
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from content_factory.agent_tools import build_tool_manifest, dispatch_tool
from content_factory.cache import ContentCache
from content_factory.config import Settings, get_settings
from content_factory.image_engine import apply_ops, export_bytes, load_image
from content_factory.media import MediaLibrary
from content_factory.models import ReCookMode, ReCookRequest
from content_factory.recook import RecookPipeline
from content_factory.sandbox import Sandbox
from content_factory.perception import (
    AudioPerception,
    build_audio_perception,
)
from content_factory.service import ContentFactoryService
from content_factory.store import Store
from content_factory.tts import TTSEngine
from content_factory.vision import detect_scene_cuts, score_best_frame

mcp = MCPServer("ai-content-factory")

# Process-local, disk-backed media library shared with the web app.
_settings: Settings = get_settings()
_service = ContentFactoryService(_settings)
_media = MediaLibrary(_settings.media_dir, cache=ContentCache(_settings.cache_dir))
_store = Store()
_recook = RecookPipeline(_settings, _media)
_tts = TTSEngine(_settings)
_audio: AudioPerception = build_audio_perception(_settings)
_sandbox = Sandbox(
    [
        _settings.media_dir,
        _settings.uploads_dir,
        _settings.cache_dir,
        _settings.library_dir,
    ]
)


def _err(exc: Exception) -> str:
    """Render an exception as a stable ``error: ...`` tool result."""
    return f"error: {exc}"


def _media_path(media_id: str) -> Path:
    """Resolve a media item's backing file (guaranteed inside the sandbox)."""
    item = _media.require(media_id)
    path = _media.path_for(item)
    if path is None:
        raise FileNotFoundError(f"media file for '{media_id}' is missing")
    return path


def _ffmpeg() -> str:
    import shutil

    binary = shutil.which("ffmpeg")
    if binary is None:
        raise RuntimeError("ffmpeg is required for video/audio operations.")
    return binary


# --- Media library -----------------------------------------------------------


@mcp.tool()
def media_list() -> str:
    """List every item in the universal media library (JSON)."""
    items = _media.list()
    return (
        "\n".join(
            f"{i.id} | {i.kind.value} | {i.filename} | {i.duration_seconds or '-'}s"
            f" | transcript={len(i.transcription.split())}w"
            for i in items
        )
        or "(empty library)"
    )


@mcp.tool()
def media_upload(path: str, language: str = "en") -> str:
    """Upload a local file (inside the sandbox) into the media library."""
    try:
        p = _sandbox.resolve(path)
        if not p.is_file():
            return f"error: file not found: {path}"
        item = _media.upload(p.name, p.read_bytes(), language=language)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return (
        f"uploaded {item.id} | {item.kind.value} | {item.filename} | "
        f"{item.size_bytes}B | duration={item.duration_seconds or '-'}s"
    )


@mcp.tool()
def media_get(media_id: str) -> str:
    """Fetch one media item including its AI reading (transcription/text)."""
    try:
        item = _media.require(media_id)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    reading = item.transcription or item.text_content or "(not transcribed)"
    return (
        f"{item.id} | {item.filename} | {item.kind.value}\n"
        f"duration={item.duration_seconds or '-'}s\n"
        f"READING:\n{reading[:2000]}"
    )


@mcp.tool()
def media_transcribe(media_id: str, language: str = "en") -> str:
    """Transcribe a video/audio item so an AI agent can read it (cached)."""
    try:
        item = _media.transcribe(media_id, language=language)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return (
        f"transcribed {item.id} | {item.filename} | "
        f"{len(item.transcription.split())} words\n{item.transcription[:2000]}"
    )


@mcp.tool()
def media_extract_text(media_id: str) -> str:
    """Extract plain text from a document item."""
    try:
        item = _media.extract_text(media_id)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    words = len(item.text_content.split())
    return f"extracted {words} words\n{item.text_content[:2000]}"


@mcp.tool()
def media_recook(
    media_id: str,
    new_title: str,
    language: str = "en",
    target_seconds: int = 60,
    mode: str = "balanced",
    change_music: bool = True,
) -> str:
    """Re-cook a media item into a brand-new project + re-worded script."""
    try:
        req = ReCookRequest(
            new_title=new_title,
            language=language,
            target_seconds=max(15, min(600, target_seconds)),
            mode=ReCookMode(mode),
            change_music=change_music,
        )
        result = _recook.run(media_id, req, _store)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return (
        f"re-cooked -> project {result.project_id} | {result.new_title}\n"
        f"mode={result.mode.value} | est {result.estimated_seconds}s | "
        f"status={result.status}\nSCRIPT:\n{result.script[:2000]}"
    )


# --- Image editing -----------------------------------------------------------


@mcp.tool()
def image_crop(
    media_id: str, left: int, top: int, width: int, height: int, out: str
) -> str:
    """Crop an image item to a fixed box and write the result to ``out``."""
    try:
        src = _media_path(media_id).read_bytes()
        img = apply_ops(
            src,
            [
                {
                    "name": "crop",
                    "params": {
                        "left": left,
                        "top": top,
                        "width": width,
                        "height": height,
                    },
                }
            ],
        )
        dst = _sandbox.resolve(out)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(export_bytes(img, "png"))
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return f"cropped {media_id} -> {dst}"


@mcp.tool()
def image_remove_background(media_id: str, out: str, tolerance: float = 0.25) -> str:
    """Remove the background of an image (chroma-key) and write ``out``."""
    try:
        src = _media_path(media_id).read_bytes()
        img = apply_ops(
            src,
            [{"name": "remove_background", "params": {"tolerance": tolerance}}],
        )
        dst = _sandbox.resolve(out)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(export_bytes(img, "png"))
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return f"background removed {media_id} -> {dst}"


@mcp.tool()
def image_upscale(media_id: str, scale: float, out: str) -> str:
    """Upscale an image by ``scale`` (Lanczos) and write ``out``."""
    try:
        src = _media_path(media_id).read_bytes()
        img = load_image(src)
        w, h = img.size
        img = img.resize((int(w * scale), int(h * scale)))
        dst = _sandbox.resolve(out)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(export_bytes(img, "png"))
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return f"upscaled {media_id} x{scale} -> {dst}"


# --- Video editing -----------------------------------------------------------


@mcp.tool()
def video_cut_clip(
    media_id: str, start_seconds: float, end_seconds: float, out: str
) -> str:
    """Cut a clip from a video item (ffmpeg, stream copy) to ``out``."""
    try:
        src = _media_path(media_id)
        dst = _sandbox.resolve(out)
        dst.parent.mkdir(parents=True, exist_ok=True)
        duration = max(0.0, end_seconds - start_seconds)
        proc = subprocess.run(
            [
                _ffmpeg(),
                "-y",
                "-ss",
                f"{start_seconds:.3f}",
                "-i",
                str(src),
                "-t",
                f"{duration:.3f}",
                "-c",
                "copy",
                str(dst),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0 or not dst.is_file():
            raise RuntimeError(proc.stderr.strip().splitlines()[-1:] or ["cut failed"])
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return f"cut {media_id} [{start_seconds}s..{end_seconds}s] -> {dst}"


@mcp.tool()
def video_concat_clips(media_ids: list[str], out: str) -> str:
    """Concatenate video items in order (ffmpeg concat demuxer) to ``out``."""
    try:
        dst = _sandbox.resolve(out)
        dst.parent.mkdir(parents=True, exist_ok=True)
        list_file = dst.with_suffix(".concat.txt")
        lines = []
        for media_id in media_ids:
            path = _media_path(media_id)
            lines.append(f"file '{path.as_posix()}'")
        list_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        proc = subprocess.run(
            [
                _ffmpeg(),
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_file),
                "-c",
                "copy",
                str(dst),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        list_file.unlink(missing_ok=True)
        if proc.returncode != 0 or not dst.is_file():
            raise RuntimeError(
                proc.stderr.strip().splitlines()[-1:] or ["concat failed"]
            )
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return f"concatenated {len(media_ids)} clips -> {dst}"


@mcp.tool()
def video_detect_scene_cuts(media_id: str, threshold: float = 30.0) -> str:
    """Detect scene cuts in a video (non-vision histogram) and list segments."""
    try:
        path = _media_path(media_id)
        cuts = detect_scene_cuts(path, threshold=threshold)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    if not cuts:
        return "no scene cuts detected"
    lines = [f"{c.start_seconds:.2f}s .. {c.end_seconds:.2f}s" for c in cuts]
    return f"{len(cuts)} scene(s)\n" + "\n".join(lines)


@mcp.tool()
def video_score_best_frame(media_id: str, top_k: int = 1) -> str:
    """Score frames and return the best ``top_k`` timestamps (heuristic)."""
    try:
        path = _media_path(media_id)
        best = score_best_frame(path, top_k=top_k)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    if not best:
        return "no frames scored"
    lines = [
        f"{entry.timestamp_seconds:.2f}s score={entry.score} ({entry.reason})"
        for entry in best
    ]
    return "best frame(s):\n" + "\n".join(lines)


# --- Voice / TTS -------------------------------------------------------------


@mcp.tool()
def voice_synthesize_speech(
    text: str, language: str = "en", out: str = "", pitch: float = 1.0
) -> str:
    """Synthesize speech for ``text`` and write MP3 to ``out`` (or return it)."""
    import asyncio

    try:
        data, duration, engine = asyncio.run(_tts.synthesize(text, language, pitch))
        if out:
            dst = _sandbox.resolve(out)
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(data)
            return f"synthesized {engine} {duration:.2f}s -> {dst}"
        return f"synthesized {engine} {duration:.2f}s\n{duration:.2f}s of mp3 audio"
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


# --- Audio perception (optional "hearing" of the soundtrack) -----------------


@mcp.tool()
def audio_detect_silence_and_pace(media_id: str) -> str:
    """Find silent gaps and a coarse speaking pace in a media item (free)."""
    try:
        path = _media_path(media_id)
        segments, pace = _audio.detect_silence_and_pace(path)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    lines = [
        f"total={pace.total_duration}s speech={pace.speech_ratio:.0%} "
        f"avg_silence={pace.avg_silence_seconds}s"
    ]
    for seg in segments:
        lines.append(f"  silence {seg.start_seconds:.2f}s..{seg.end_seconds:.2f}s")
    return "\n".join(lines) or "(no audio)"


@mcp.tool()
def audio_classify_music_mood(media_id: str) -> str:
    """Classify a coarse music mood from acoustic features (free, non-AI)."""
    try:
        path = _media_path(media_id)
        mood = _audio.classify_music_mood(path)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return (
        f"mood={mood.mood} | energy={mood.energy} | tempo≈{mood.tempo_bpm:.0f}bpm\n"
        f"{mood.description}"
    )


@mcp.tool()
def audio_check_quality(media_id: str) -> str:
    """Report basic technical audio quality (free, non-AI)."""
    try:
        path = _media_path(media_id)
        q = _audio.check_audio_quality(path)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return (
        f"sr={q.sample_rate}Hz peak={q.peak_db}dB "
        f"clipping={'yes' if q.clipping else 'no'} "
        f"dc_offset={q.dc_offset} noise_floor={q.noise_floor_db}dB"
    )


@mcp.tool()
def audio_detect_events(media_id: str) -> str:
    """Detect sound events (applause, bells, music swell). Needs an AI backend."""
    try:
        path = _media_path(media_id)
        events = _audio.detect_audio_events(path)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    if not events:
        return "no audio events detected"
    lines = [
        f"{e.label} | {e.start_seconds:.2f}s..{e.end_seconds:.2f}s "
        f"conf={e.confidence:.2f}"
        for e in events
    ]
    return "\n".join(lines)


@mcp.tool()
def audio_diarize_speakers(media_id: str) -> str:
    """Separate 'who speaks when'. Needs an AI backend (pyannote)."""
    try:
        path = _media_path(media_id)
        turns = _audio.diarize_speakers(path)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    if not turns:
        return "no speakers detected"
    return "\n".join(
        f"{t.speaker_id} | {t.start_seconds:.2f}s..{t.end_seconds:.2f}s"
        for t in turns
    )


@mcp.tool()
def audio_detect_speech_emotion(media_id: str) -> str:
    """Classify the dominant emotion in speech. Needs an AI backend (SER)."""
    try:
        path = _media_path(media_id)
        emotion = _audio.detect_speech_emotion(path)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return f"emotion={emotion.emotion} conf={emotion.confidence:.2f}"


@mcp.tool()
def audio_describe_scene(media_id: str) -> str:
    """Describe the whole soundtrack naturally. Needs an audio-capable LLM."""
    try:
        path = _media_path(media_id)
        scene = _audio.describe_audio_scene(path)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return scene.description


@mcp.tool()
def factory_list_tools() -> str:
    """List all 61 AI Content Factory pipeline/editing tools with categories and parameters."""
    import json

    return json.dumps(build_tool_manifest(), ensure_ascii=False, indent=2)


@mcp.tool()
def factory_call_tool(tool_name: str, args_json: str = "{}") -> str:
    """Execute any of the 61 AI Content Factory pipeline/editing tools by name with JSON args."""
    import json

    try:
        args = json.loads(args_json) if args_json.strip() else {}
        result = dispatch_tool(_service, tool_name, args)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)

    if args.transport == "sse":
        mcp.run(transport="sse", host=args.host, port=args.port)
    else:
        mcp.run(transport="stdio")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
