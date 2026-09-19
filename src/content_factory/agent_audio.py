"""Audio-denoise agent tool, split out of ``agent_tools.py``.

Kept in its own module so ``agent_tools.py`` stays under its line budget while
the registry still exposes ``audio_denoise`` through the same manifest (and
therefore through the MCP server's ``factory_call_tool``).
"""

from __future__ import annotations

from typing import Any

from .agent_schema import ToolSpec, _p


def _h_audio_denoise(service: Any, args: Any) -> Any:
    """Remove background noise from an audio asset via spectral gating."""
    return service.audio_denoise(
        args.ident("ref"),
        strength=args.number_or("strength", 0.8),
        noise_profile_ref=args.optional_string("noise_profile_ref"),
        format=args.string("format", "mp3"),
    )


def _h_download_audio_clip(service: Any, args: Any) -> Any:
    """Download any audio by URL, optionally cutting a specific clip range."""
    return service.download_audio_clip(
        args.string("url"),
        start_seconds=args.number_or("start_seconds", 0.0),
        end_seconds=args.number_or("end_seconds", 0.0),
        language=args.string("language", "vi"),
    )


def audio_tool_specs() -> list[Any]:
    """Build the audio tool specs."""
    return [
        ToolSpec(
            "audio_denoise",
            "Remove background noise from an audio asset via spectral gating.",
            "audio",
            "audio_denoise",
            _h_audio_denoise,
            {
                "ref": _p("string", "Media id, edited asset id, or path."),
                "strength": _p(
                    "number", "0-1, how aggressively noise is suppressed (default 0.8)."
                ),
                "noise_profile_ref": _p(
                    "string|null",
                    "Optional asset holding a pure-noise sample to learn from.",
                ),
                "format": _p("string", "Output format: mp3 or wav (default mp3)."),
            },
            ("ref",),
        ),
        ToolSpec(
            "download_audio_clip",
            "Download any audio by URL, optionally cutting a specific clip range.",
            "audio",
            "download_audio_clip",
            _h_download_audio_clip,
            {
                "url": _p(
                    "string", "Any audio/video URL (YouTube, podcast, direct MP3)."
                ),
                "start_seconds": _p("number", "Clip start in seconds (default 0)."),
                "end_seconds": _p("number", "Clip end in seconds (0 = full audio)."),
                "language": _p("string", "BCP-47 code, 'vi' default."),
            },
            ("url",),
        ),
    ]
