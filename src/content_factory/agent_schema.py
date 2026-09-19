"""Shared vocabulary for the agent-facing tool registry.

Every tool is described by a :class:`ToolSpec`, its arguments are read through
:class:`Args`, and its schema is written with :func:`_p`.  Those primitives used
to live in ``agent_tools.py`` next to the registry, which forced the per-domain
spec modules (``agent_audio``, ``agent_photo``, ...) to import them *lazily* to
dodge a circular import: ``agent_tools`` imports the domains, and the domains
imported it back.

They live here instead.  The dependency now points one way — domains import this
module, ``agent_tools`` imports the domains — so the lazy-import workaround is
gone and the tool DSL has a single home.  ``agent_tools`` still re-exports the
public names for callers that import them from there.
"""

from __future__ import annotations

import base64 as _base64
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from .models import SEO_METRICS, SEO_PLATFORMS

__all__ = [
    "ASSET",
    "AUDIO_TRACKS",
    "IMAGE_LAYERS",
    "PACK",
    "PROJECT",
    "REF",
    "SCENE",
    "TIMELINE_PATCH",
    "Args",
    "ToolError",
    "ToolSpec",
]


class ToolError(Exception):
    """Raised when a tool call cannot be executed as requested."""


# ---------------------------------------------------------------------------
# Argument reading
# ---------------------------------------------------------------------------


class Args:
    """Typed, validating reader over one tool call's JSON arguments.

    Every accessor raises :class:`ToolError` with the argument name in the
    message, so an agent that guessed wrong gets told exactly which field to
    fix rather than a stack trace.
    """

    def __init__(self, raw: dict[str, Any] | None = None) -> None:
        self._raw: dict[str, Any] = dict(raw or {})

    def raw(self) -> dict[str, Any]:
        return dict(self._raw)

    def _value(self, key: str, default: Any = None) -> Any:
        value = self._raw.get(key, default)
        return default if value is None else value

    def requires(self, key: str) -> Any:
        if key not in self._raw or self._raw[key] is None:
            raise ToolError(f"Missing required argument '{key}'.")
        return self._raw[key]

    def ident(self, key: str) -> str:
        return self._check_id(self.requires(key), key)

    def optional_ident(self, key: str) -> str | None:
        value = self._raw.get(key)
        if value is None:
            return None
        return self._check_id(value, key)

    def string(self, key: str, default: str = "") -> str:
        return str(self._value(key, default))

    def optional_string(self, key: str) -> str | None:
        value = self._raw.get(key)
        return None if value is None else str(value)

    def integer(self, key: str, default: int = 0) -> int:
        try:
            return int(self._value(key, default))
        except (TypeError, ValueError) as exc:
            raise ToolError(f"Argument '{key}' must be an integer.") from exc

    def number(self, key: str, default: float | None = None) -> float | None:
        value = self._raw.get(key, default)
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise ToolError(f"Argument '{key}' must be a number.") from exc

    def number_or(self, key: str, default: float) -> float:
        value = self.number(key, default)
        return default if value is None else value

    def boolean(self, key: str, default: bool = False) -> bool:
        value = self._raw.get(key, default)
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    def numbers(self, key: str, default: Sequence[float] = ()) -> list[float]:
        value = self._raw.get(key, list(default))
        if not isinstance(value, list):
            raise ToolError(f"Argument '{key}' must be a list of numbers.")
        try:
            return [float(item) for item in value]
        except (TypeError, ValueError) as exc:
            raise ToolError(f"Argument '{key}' must be a list of numbers.") from exc

    def strings(self, key: str, default: Sequence[str] = ()) -> list[str]:
        value = self._raw.get(key, list(default))
        if not isinstance(value, list):
            raise ToolError(f"Argument '{key}' must be a list of strings.")
        return [str(item) for item in value]

    def objects(
        self, key: str, default: Sequence[dict[str, Any]] = ()
    ) -> list[dict[str, Any]]:
        value = self._raw.get(key, list(default))
        if not isinstance(value, list) or not all(isinstance(i, dict) for i in value):
            raise ToolError(f"Argument '{key}' must be a list of objects.")
        return [dict(item) for item in value]

    def mapping(
        self, key: str, default: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        value = self._raw.get(key, default if default is not None else {})
        if not isinstance(value, dict):
            raise ToolError(f"Argument '{key}' must be an object.")
        return dict(value)

    def choice(self, key: str, allowed: Sequence[str], default: str) -> str:
        value = str(self._value(key, default))
        if value not in allowed:
            raise ToolError(
                f"Argument '{key}' must be one of {sorted(allowed)}, got '{value}'."
            )
        return value

    def base64(self, key: str) -> bytes:
        raw = str(self.requires(key))
        try:
            return _base64.b64decode(raw, validate=False)
        except Exception as exc:
            raise ToolError(f"Argument '{key}' must be base64 data.") from exc

    @staticmethod
    def _check_id(value: Any, key: str) -> str:
        text = str(value)
        if not _VALID_ID.match(text):
            raise ToolError(f"Argument '{key}' must be a short id string.")
        return text


_VALID_ID = re.compile(r"^[A-Za-z0-9_\-:.]{1,80}$")


# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------


def _p(type_: str, description: str, **extra: Any) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": type_, "description": description}
    schema.update(extra)
    return schema


PROJECT = _p("string", "Project id from list_projects / create_project.")
SCENE = _p("string", "Scene id from get_project -> video_project.scenes[].id.")
REF = _p(
    "string",
    "Media-library id, edited asset id (from an earlier media tool), "
    "or a path inside the media roots.",
)
ASSET = _p("string", "asset_id or url returned by an earlier media/studio tool.")
_PLATFORM = _p(
    "string",
    "Target platform; 'all' scores every platform in one call.",
    enum=list(SEO_PLATFORMS),
    default="youtube",
)
_METRIC = _p(
    "string",
    "Rate being tested.",
    enum=list(SEO_METRICS),
    default="ctr",
)
#: ``calibrate`` fits weights per profile, so 'all' is not a valid target there.
_CALIBRATION_PLATFORMS: tuple[str, ...] = ("youtube", "youtube_shorts", "tiktok")
PACK = _p(
    "object",
    "Publish pack: title, description, tags, hashtags, keywords, script, hook, "
    "duration_seconds, aspect_ratio, thumbnail_present, thumbnail_text, "
    "on_screen_text, has_captions, caption_source, has_chapters, chapter_count, "
    "has_end_screen, playlist, sound, sound_trending, beat_synced, bpm, "
    "cuts_per_minute, loop_friendly, intro_seconds, text_in_safe_zone, "
    "publish_hour, audience_hours, watermark, comment_prompt, series_part, "
    "duet_stitch_enabled, channel, language, engagement.",
)
TIMELINE_PATCH = _p(
    "object",
    "Scene fields to change, e.g. {grade: 'teal-orange', filter: 'cool', "
    "transition: 'fade'}.",
)
AUDIO_TRACKS = _p(
    "array",
    "Tracks to mix. role='voice' lets that track duck the others.",
    items=_p(
        "object",
        "One track: ref, gain_db, offset_seconds, loop, role.",
        properties={
            "ref": REF,
            "gain_db": _p("number", "Gain in dB, e.g. -6."),
            "offset_seconds": _p("number", "Delay before this track starts."),
            "loop": _p("boolean", "Repeat the track until the mix ends."),
            "role": _p("string", "Free label; 'voice' enables ducking."),
        },
        required=["ref"],
    ),
)
IMAGE_LAYERS = _p(
    "array",
    "Images to composite on the base, bottom-most first.",
    items=_p(
        "object",
        "One layer: ref plus placement.",
        properties={
            "ref": REF,
            "x": _p(
                "string|number",
                "Left offset, a percentage ('50%'), or 'left'/'center'/'right'.",
            ),
            "y": _p(
                "string|number",
                "Top offset, a percentage, or 'top'/'center'/'bottom'. "
                "A corner like x='bottom-right' is also accepted.",
            ),
            "scale": _p("number", "Resize factor, 1.0 keeps the size."),
            "opacity": _p("number", "0..1 alpha for the layer."),
            "rotate": _p("number", "Degrees, counter-clockwise."),
            "blend": _p(
                "string",
                "normal|multiply|screen|overlay|hard_light|soft_light|add|difference.",
            ),
        },
        required=["ref"],
    ),
)


@dataclass(frozen=True)
class ToolSpec:
    """One callable capability, with the schema an agent reads before calling."""

    name: str
    description: str
    category: str
    service: str
    handler: Callable[[Any, Args], Any]
    properties: dict[str, Any] = field(default_factory=dict)
    required: tuple[str, ...] = ()
    #: Phrases a caller types when they mean this tool ("lower the music
    #: under the voice" -> duck_music).  Descriptions are written to be read;
    #: these are written to be searched, and ``search_tools`` weights them
    #: higher than a mere substring of a description.
    keywords: tuple[str, ...] = ()

    @property
    def input_schema(self) -> dict[str, Any]:
        """JSON Schema (draft-07 subset) for this tool's arguments object."""
        schema: dict[str, Any] = {
            "type": "object",
            "properties": dict(self.properties),
            "additionalProperties": False,
        }
        if self.required:
            schema["required"] = list(self.required)
        return schema

    def manifest_entry(self) -> dict[str, Any]:
        """The public description of this tool."""
        return {
            "name": self.name,
            "description": self.description,
            "service": self.service,
            "category": self.category,
            "keywords": list(self.keywords),
            "input_schema": self.input_schema,
            # Kept for older readers: a flat field -> type summary.
            "args": {
                key: str(value.get("type", "any"))
                + ("" if key in self.required else " (optional)")
                for key, value in self.properties.items()
            },
        }
