"""Video/audio effect and accessibility agent tools, split out of ``agent_tools.py``.

Kept in their own module so ``agent_tools.py`` stays under its line budget while
the registry still exposes the tools through the same manifest (and therefore
through the MCP server's ``factory_call_tool``).
"""

from __future__ import annotations

from typing import Any

from .agent_schema import ToolSpec, _p


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


def _h_analyze_audio(service: Any, args: Any) -> Any:
    return service.analyze_audio(args.base64("audio_b64"))


def _h_sfx_catalog(service: Any, args: Any) -> Any:
    return service.sfx_catalog()


def _h_synthesize_sfx(service: Any, args: Any) -> Any:
    return service.synthesize_sfx(
        args.string("name"),
        args.mapping("params") or None,
        export_format=args.string("format", "wav"),
    )


def _h_audio_operation_catalog(service: Any, args: Any) -> Any:
    return service.audio_operation_catalog()


def _h_describe_audio_operation(service: Any, args: Any) -> Any:
    return service.describe_audio_operation(args.string("name"))


def _h_describe_audio(service: Any, args: Any) -> Any:
    return service.describe_audio(args.base64("audio_b64"))


def _h_suggest_audio_mastering(service: Any, args: Any) -> Any:
    return service.suggest_audio_mastering(args.base64("audio_b64"))


def _h_apply_audio_mastering(service: Any, args: Any) -> Any:
    return service.apply_audio_mastering(
        args.base64("audio_b64"),
        export_format=args.string("format", "wav"),
    )


def _h_ai_audio_catalog(service: Any, args: Any) -> Any:
    return service.ai_audio_catalog()


def _h_dub_audio(service: Any, args: Any) -> Any:
    return service.dub_audio(
        args.base64("audio_b64"),
        args.string("target_text"),
        lang=args.string("lang", "en"),
    )


def _h_voice_clone(service: Any, args: Any) -> Any:
    return service.voice_clone(
        args.base64("audio_b64"),
        args.base64("ref_voice"),
    )


def _h_stem_catalog(service: Any, args: Any) -> Any:
    return service.stem_catalog()


def _h_separate_audio_stems(service: Any, args: Any) -> Any:
    return service.separate_audio_stems(
        args.base64("audio_b64"),
        args.number("num", 2),
        export_format=args.string("format", "wav"),
    )


def video_tool_specs() -> list[Any]:
    """Build the video/audio tool specs."""
    return [
        ToolSpec(
            "video_effect_catalog",
            "List every video frame effect (glitch, shake, glow, film grain…) "
            "with a plain-language description of each.",
            "media",
            "video_effect_catalog",
            _h_video_effect_catalog,
        ),
        ToolSpec(
            "apply_video_effect",
            "Apply a frame effect to an image (or a video frame) and save the result.",
            "media",
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
            "media",
            "audio_effect_catalog",
            _h_audio_effect_catalog,
        ),
        ToolSpec(
            "apply_audio_effect",
            "Apply a DSP effect to audio bytes and save the result.",
            "media",
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
            "media",
            "video_operation_catalog",
            _h_video_operation_catalog,
        ),
        ToolSpec(
            "describe_video_operation",
            "Explain one video/audio operation in plain language.",
            "media",
            "describe_video_operation",
            _h_describe_video_operation,
            {"name": _p("string", "The operation name, e.g. split_scene.")},
            ("name",),
        ),
        ToolSpec(
            "describe_video_timeline",
            "Summarise a project's timeline in natural language (scene count, "
            "runtime, words, looks) — no vision required.",
            "media",
            "describe_video_timeline",
            _h_describe_video_timeline,
            {"project_id": _p("string", "The project id.")},
            ("project_id",),
        ),
        ToolSpec(
            "suggest_video_edits",
            "Turn a timeline's report into concrete edit suggestions.",
            "media",
            "suggest_video_edits",
            _h_suggest_video_edits,
            {"project_id": _p("string", "The project id.")},
            ("project_id",),
        ),
        ToolSpec(
            "analyze_audio",
            "Measure an audio clip: waveform, spectrogram, frequency spectrum, "
            "RMS, dynamic range, clipping, noise floor — no ears required.",
            "audio",
            "analyze_audio",
            _h_analyze_audio,
            {"audio_b64": _p("string", "Base64 audio (mp3/wav).")},
            ("audio_b64",),
        ),
        ToolSpec(
            "sfx_catalog",
            "List every synthesised sound effect (whoosh, impact, explosion…) "
            "with a plain-language description.",
            "audio",
            "sfx_catalog",
            _h_sfx_catalog,
        ),
        ToolSpec(
            "synthesize_sfx",
            "Generate a sound effect from scratch and save it.",
            "audio",
            "synthesize_sfx",
            _h_synthesize_sfx,
            {
                "name": _p("string", "SFX name, e.g. whoosh."),
                "params": _p("object", "Optional duration/seed."),
                "format": _p("string", "wav or mp3."),
            },
            ("name",),
        ),
        ToolSpec(
            "audio_operation_catalog",
            "List every audio operation grouped by category, with plain-language "
            "descriptions — the accessibility map of the audio editor.",
            "audio",
            "audio_operation_catalog",
            _h_audio_operation_catalog,
        ),
        ToolSpec(
            "describe_audio_operation",
            "Explain one audio operation in plain language.",
            "audio",
            "describe_audio_operation",
            _h_describe_audio_operation,
            {"name": _p("string", "The operation name, e.g. audio_mix.")},
            ("name",),
        ),
        ToolSpec(
            "describe_audio",
            "Describe an audio clip in plain language from its measurements.",
            "audio",
            "describe_audio",
            _h_describe_audio,
            {"audio_b64": _p("string", "Base64 audio (mp3/wav).")},
            ("audio_b64",),
        ),
        ToolSpec(
            "suggest_audio_mastering",
            "Auto-suggest a mastering chain from an audio clip's measurements.",
            "audio",
            "suggest_audio_mastering",
            _h_suggest_audio_mastering,
            {"audio_b64": _p("string", "Base64 audio (mp3/wav).")},
            ("audio_b64",),
        ),
        ToolSpec(
            "apply_audio_mastering",
            "Run the auto-suggested mastering chain (denoise → effects → "
            "loudness normalise) and persist the mastered audio.",
            "audio",
            "apply_audio_mastering",
            _h_apply_audio_mastering,
            {
                "audio_b64": _p("string", "Base64 audio (mp3/wav)."),
                "format": _p("string", "wav or mp3."),
            },
            ("audio_b64",),
        ),
        ToolSpec(
            "ai_audio_catalog",
            "List every AI audio capability (dub, voice_clone, separate) with a "
            "plain-language description and adapter status.",
            "audio",
            "ai_audio_catalog",
            _h_ai_audio_catalog,
        ),
        ToolSpec(
            "dub_audio",
            "Dub a clip via a registered ML adapter. Fails with a clear error "
            "until an adapter is configured.",
            "audio",
            "dub_audio",
            _h_dub_audio,
            {
                "audio_b64": _p("string", "Base64 audio (mp3/wav)."),
                "target_text": _p("string", "The target script to speak."),
                "lang": _p("string", "Target language code."),
            },
            ("audio_b64", "target_text"),
        ),
        ToolSpec(
            "voice_clone",
            "Clone a voice via a registered ML adapter. Fails with a clear "
            "error until an adapter is configured.",
            "audio",
            "voice_clone",
            _h_voice_clone,
            {
                "audio_b64": _p("string", "Base64 source audio."),
                "ref_voice": _p("string", "Base64 reference voice sample."),
            },
            ("audio_b64", "ref_voice"),
        ),
        ToolSpec(
            "stem_catalog",
            "List every available audio stem (voice, instrumental, low/mid/high) "
            "with a plain-language description.",
            "audio",
            "stem_catalog",
            _h_stem_catalog,
        ),
        ToolSpec(
            "separate_audio_stems",
            "Separate a mono clip into stems (voice/instrumental or low/mid/high) "
            "and persist each stem.",
            "audio",
            "separate_audio_stems",
            _h_separate_audio_stems,
            {
                "audio_b64": _p("string", "Base64 audio (mp3/wav)."),
                "num": _p("number", "2 = voice/instrumental, 3 = low/mid/high."),
                "format": _p("string", "wav or mp3."),
            },
            ("audio_b64",),
        ),
    ]
