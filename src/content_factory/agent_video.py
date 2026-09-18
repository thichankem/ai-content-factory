"""Video/audio effect and accessibility agent tools, split out of ``agent_tools.py``.

Kept in their own module so ``agent_tools.py`` stays under its line budget while
the registry still exposes the tools through the same manifest (and therefore
through the MCP server's ``factory_call_tool``).
"""

from __future__ import annotations

from typing import Any


def _h_video_effect_catalog(service: Any, args: Any) -> Any:
    return service.video_effect_catalog()


def _h_apply_video_effect(service: Any, args: Any) -> Any:
    return service.apply_video_effect(
        args.base64("image_b64"),
        args.string("name"),
        args.mapping("params") or None,
        export_format=args.string("format", "png"),
    )


def _h_audio_effect_catalog(service: Any, args: Any) -> Any:
    return service.audio_effect_catalog()


def _h_apply_audio_effect(service: Any, args: Any) -> Any:
    return service.apply_audio_effect(
        args.base64("audio_b64"),
        args.string("name"),
        args.mapping("params") or None,
        export_format=args.string("format", "mp3"),
    )


def _h_video_operation_catalog(service: Any, args: Any) -> Any:
    return service.video_operation_catalog()


def _h_describe_video_operation(service: Any, args: Any) -> Any:
    return service.describe_video_operation(args.string("name"))


def _h_describe_video_timeline(service: Any, args: Any) -> Any:
    return service.describe_video_timeline(args.ident("project_id"))


def _h_suggest_video_edits(service: Any, args: Any) -> Any:
    return service.suggest_video_edits(args.ident("project_id"))


def video_tool_specs() -> list[Any]:
    """Build the video/audio tool specs (lazy import to avoid a cycle)."""
    from .agent_tools import ToolSpec, _p

    return [
        ToolSpec(
            "video_effect_catalog",
            "List every video frame effect (glitch, shake, glow, film grain…) "
            "with a plain-language description of each.",
            "video",
            "video_effect_catalog",
            _h_video_effect_catalog,
        ),
        ToolSpec(
            "apply_video_effect",
            "Apply a frame effect to an image (or a video frame) and save the result.",
            "video",
            "apply_video_effect",
            _h_apply_video_effect,
            {
                "image_b64": _p("string", "Base64 of a png/jpeg/webp image."),
                "name": _p("string", "Effect name, e.g. glitch."),
                "params": _p("object", "Effect parameters."),
                "format": _p("string", "png, jpeg or webp."),
            },
            ("image_b64", "name"),
        ),
        ToolSpec(
            "audio_effect_catalog",
            "List every audio DSP effect (equalizer, compressor, reverb, voice "
            "changer…) with a plain-language description.",
            "video",
            "audio_effect_catalog",
            _h_audio_effect_catalog,
        ),
        ToolSpec(
            "apply_audio_effect",
            "Apply a DSP effect to audio bytes and save the result.",
            "video",
            "apply_audio_effect",
            _h_apply_audio_effect,
            {
                "audio_b64": _p("string", "Base64 audio (mp3/wav)."),
                "name": _p("string", "Effect name, e.g. reverb."),
                "params": _p("object", "Effect parameters."),
                "format": _p("string", "mp3 or wav."),
            },
            ("audio_b64", "name"),
        ),
        ToolSpec(
            "video_operation_catalog",
            "List every video/audio editing operation grouped by category, with "
            "plain-language descriptions — the accessibility map of the editor.",
            "video",
            "video_operation_catalog",
            _h_video_operation_catalog,
        ),
        ToolSpec(
            "describe_video_operation",
            "Explain one video/audio operation in plain language.",
            "video",
            "describe_video_operation",
            _h_describe_video_operation,
            {"name": _p("string", "The operation name, e.g. split_scene.")},
            ("name",),
        ),
        ToolSpec(
            "describe_video_timeline",
            "Summarise a project's timeline in natural language (scene count, "
            "runtime, words, looks) — no vision required.",
            "video",
            "describe_video_timeline",
            _h_describe_video_timeline,
            {"project_id": _p("string", "The project id.")},
            ("project_id",),
        ),
        ToolSpec(
            "suggest_video_edits",
            "Turn a timeline's report into concrete edit suggestions.",
            "video",
            "suggest_video_edits",
            _h_suggest_video_edits,
            {"project_id": _p("string", "The project id.")},
            ("project_id",),
        ),
    ]
