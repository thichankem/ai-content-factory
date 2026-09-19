"""YouTube search & download agent tools, split out of ``agent_tools.py``.

Kept in its own module so ``agent_tools.py`` stays under its line budget while
the registry still exposes ``youtube_search`` and ``youtube_download`` through
the same manifest (and therefore through the MCP server's ``factory_call_tool``).
"""

from __future__ import annotations

from typing import Any

from .agent_schema import ToolSpec, _p


def _h_youtube_search(service: Any, args: Any) -> Any:
    """Search YouTube for videos matching a query (metadata only)."""
    return service.search_youtube(args.string("query"), args.integer("limit", 8))


def _h_youtube_download(service: Any, args: Any) -> Any:
    """Download a YouTube video (by URL or id) into the media library."""
    return service.youtube_download(
        args.string("url"),
        language=args.string("language", "vi"),
        extract_audio=args.boolean("extract_audio", False),
        auto_transcribe=args.boolean("auto_transcribe", False),
    )


def _h_youtube_transcript(service: Any, args: Any) -> Any:
    """Get a transcript for a YouTube video by any means (subtitles or whisper)."""
    return service.youtube_transcript(
        args.string("url"), language=args.string("language", "en")
    )


def youtube_tool_specs() -> list[Any]:
    """Build the two YouTube tool specs."""
    return [
        ToolSpec(
            "youtube_search",
            "Search YouTube for videos matching a query (title, id, url, duration).",
            "research",
            "search_youtube",
            _h_youtube_search,
            {
                "query": _p("string", "The YouTube search query."),
                "limit": _p("integer", "How many results to return (1-25, default 8)."),
            },
            ("query",),
        ),
        ToolSpec(
            "youtube_download",
            "Download a YouTube video (by URL or id) into the media library.",
            "media",
            "youtube_download",
            _h_youtube_download,
            {
                "url": _p("string", "YouTube URL or video id."),
                "language": _p(
                    "string", "BCP-47 code for transcription, 'vi' default."
                ),
                "extract_audio": _p(
                    "boolean", "Download only the audio track (default false)."
                ),
                "auto_transcribe": _p(
                    "boolean",
                    "Transcribe right after download (default false).",
                ),
            },
            ("url",),
        ),
        ToolSpec(
            "youtube_transcript",
            "Get a transcript for a YouTube video by any means (subtitles or whisper).",
            "media",
            "youtube_transcript",
            _h_youtube_transcript,
            {
                "url": _p("string", "YouTube URL or video id."),
                "language": _p("string", "BCP-47 code, 'en' default."),
            },
            ("url",),
        ),
    ]
