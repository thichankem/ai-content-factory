"""Agent-facing tool registry: a self-describing manifest plus dispatch.

External AI agents (Claude, Codex, DeepSeek, Gemini, ...) discover the factory
through ``GET /tools`` and execute an operation through ``POST /tools/call``.
Every tool is a thin, validated wrapper over an existing service method — the
registry never improvises business logic, so what an agent can do is exactly
what the API allows.

Design goals:

* **Machine-readable.** Each tool publishes a real JSON Schema (``input_schema``)
  under a stable protocol, so a model's tool-calling layer can consume the
  manifest without a human translating prose.
* **Text-first media.** A tool-only agent has no eyes and no ears, so the media
  tools return *text*: duration, loudness, silence, shot changes, palette,
  tempo. Anything that happens next (cut, mix, compose) is then a decision made
  on that text.
* **Chainable.** Media operations return an ``asset_id``; any later call accepts
  that id as its input, so multi-step edits are a conversation, not a file hunt.
"""

from __future__ import annotations

import base64 as _base64
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from .models import (
    SEO_METRICS,
    SEO_PLATFORMS,
    ApprovalCreate,
    ApprovalStage,
    ApprovalVerdict,
    ProjectCreate,
    PublishCreate,
    ScriptAnalyzeRequest,
    ScriptUpdate,
)

__all__ = [
    "Args",
    "TOOL_MANIFEST",
    "TOOL_REGISTRY",
    "ToolError",
    "ToolSpec",
    "build_tool_manifest",
    "dispatch_tool",
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
        except Exception as exc:  # noqa: BLE001 - any decode failure is the same error
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
            "input_schema": self.input_schema,
            # Kept for older readers: a flat field -> type summary.
            "args": {
                key: str(value.get("type", "any"))
                + ("" if key in self.required else " (optional)")
                for key, value in self.properties.items()
            },
        }


# ---------------------------------------------------------------------------
# Handlers — one small function per tool, grouped by domain
# ---------------------------------------------------------------------------


def _h_list_projects(service: Any, args: Args) -> Any:
    return service.list_projects()


def _h_get_project(service: Any, args: Args) -> Any:
    return service.get_project(args.ident("project_id"))


def _h_agent_catalog(service: Any, args: Args) -> Any:
    return service.agent_catalog()


def _h_list_script_styles(service: Any, args: Args) -> Any:
    return service.list_script_styles()


def _h_create_project(service: Any, args: Args) -> Any:
    return service.create_project(
        ProjectCreate(
            name=args.string("name"),
            topic=args.string("topic"),
            target_language=args.string("target_language", "vi"),
            duration_target_seconds=args.integer("duration_target_seconds", 45),
        )
    )


def _h_research_project(service: Any, args: Args) -> Any:
    return service.research(
        args.ident("project_id"), include_web=args.boolean("include_web", True)
    )


def _h_list_kbs(service: Any, args: Args) -> Any:
    return service.list_kbs()


def _h_attach_kb(service: Any, args: Args) -> Any:
    return service.attach_kb(args.ident("project_id"), args.optional_ident("kb_id"))


def _h_ground_project(service: Any, args: Args) -> Any:
    return service.ground_project(args.ident("project_id"))


def _h_export_brief(service: Any, args: Args) -> Any:
    return service.export_brief(args.ident("project_id"))


def _h_update_script(service: Any, args: Args) -> Any:
    return service.update_script(
        args.ident("project_id"),
        ScriptUpdate(
            script=args.string("script"),
            source_rights_confirmed=args.boolean("source_rights_confirmed", False),
        ),
    )


def _h_analyze_script(service: Any, args: Args) -> Any:
    return service.analyze_project_script(
        args.ident("project_id"), ScriptAnalyzeRequest()
    )


def _h_build_video_project(service: Any, args: Args) -> Any:
    return service.build_video_project(args.ident("project_id"))


def _h_timeline_report(service: Any, args: Args) -> Any:
    return service.timeline_report(args.ident("project_id"))


def _h_render_plan(service: Any, args: Args) -> Any:
    return service.render_plan(args.ident("project_id"))


def _h_render_video(service: Any, args: Args) -> Any:
    return service.render_video(
        args.ident("project_id"),
        args.choice("export_format", ("webm", "mp4"), "webm"),
        args.optional_string("audio_ref"),
    )


def _h_split_scene(service: Any, args: Args) -> Any:
    return service.split_video_scene(
        args.ident("project_id"),
        args.ident("scene_id"),
        at=args.number_or("at", 0.5),
    )


def _h_merge_scene(service: Any, args: Args) -> Any:
    return service.merge_video_scene(args.ident("project_id"), args.ident("scene_id"))


def _h_duplicate_scene(service: Any, args: Args) -> Any:
    return service.duplicate_video_scene(
        args.ident("project_id"), args.ident("scene_id")
    )


def _h_delete_scene(service: Any, args: Args) -> Any:
    return service.delete_video_scene(args.ident("project_id"), args.ident("scene_id"))


def _h_move_scene(service: Any, args: Args) -> Any:
    return service.move_video_scene(
        args.ident("project_id"),
        args.ident("scene_id"),
        args.integer("to_index", 0),
    )


def _h_set_scene_speed(service: Any, args: Args) -> Any:
    return service.set_scene_speed(
        args.ident("project_id"),
        args.ident("scene_id"),
        args.number_or("speed", 1.0),
    )


def _h_reverse_scene(service: Any, args: Args) -> Any:
    return service.reverse_scene(
        args.ident("project_id"),
        args.ident("scene_id"),
        args.boolean("reverse", True),
    )


def _h_trim_scene(service: Any, args: Args) -> Any:
    return service.trim_scene(
        args.ident("project_id"),
        args.ident("scene_id"),
        args.number("trim_start"),
        args.number("trim_end"),
    )


def _h_set_scene_audio(service: Any, args: Args) -> Any:
    return service.set_scene_audio(
        args.ident("project_id"),
        args.ident("scene_id"),
        args.number("volume"),
        args.number("fade_in"),
        args.number("fade_out"),
    )


def _h_bulk_update_scenes(service: Any, args: Args) -> Any:
    return service.bulk_update_video_scenes(
        args.ident("project_id"),
        args.strings("scene_ids"),
        args.mapping("patch"),
    )


def _h_set_keyframes(service: Any, args: Args) -> Any:
    return service.set_scene_keyframes(
        args.ident("project_id"), args.ident("scene_id"), args.objects("keyframes")
    )


def _h_add_marker(service: Any, args: Args) -> Any:
    return service.add_timeline_marker(
        args.ident("project_id"),
        args.number_or("time_seconds", 0.0),
        args.string("label"),
        args.string("color", "#f59e0b"),
    )


def _h_ai_assist(service: Any, args: Args) -> Any:
    return service.apply_ai_assist(
        args.ident("project_id"),
        fit=args.boolean("fit", True),
        beat=args.boolean("beat", False),
        bpm=args.integer("bpm", 120),
    )


def _h_image_presets(service: Any, args: Args) -> Any:
    return service.image_presets()


def _h_edit_image(service: Any, args: Args) -> Any:
    return service.edit_image(
        args.base64("image_b64"),
        ops=args.objects("ops"),
        preset=args.optional_string("preset"),
        export_format=args.string("format", "png"),
    )


def _h_voice_presets(service: Any, args: Args) -> Any:
    return service.voice_presets()


def _h_enhance_voice(service: Any, args: Args) -> Any:
    return service.process_voice_audio(
        args.base64("audio_b64"),
        params=args.mapping("params") or None,
        preset=args.optional_string("preset"),
        export_format=args.string("format", "mp3"),
    )


def _h_duck_music(service: Any, args: Args) -> Any:
    return service.duck_music_under_voice(
        args.base64("voice_b64"),
        args.base64("music_b64"),
        args.number_or("duck_db", -12.0),
    )


def _h_generate_voiceover(service: Any, args: Args) -> Any:
    return service.generate_voiceover(args.ident("project_id"))


def _h_start_generation(service: Any, args: Args) -> Any:
    return service.start_generation(args.ident("project_id"))


def _h_approve_stage(service: Any, args: Args) -> Any:
    stage = args.choice("stage", ("script", "video"), "script")
    verdict = args.choice("verdict", ("approved", "rejected"), "approved")
    return service.approve(
        args.ident("project_id"),
        ApprovalCreate(
            stage=ApprovalStage(stage),
            verdict=ApprovalVerdict(verdict),
            comment=args.optional_string("comment"),
        ),
    )


def _h_publish_project(service: Any, args: Args) -> Any:
    return service.publish(
        args.ident("project_id"), PublishCreate(platforms=args.strings("platforms"))
    )


# --- Media library and reading ------------------------------------------------


def _h_list_media(service: Any, args: Args) -> Any:
    return service.media_list()


def _h_get_media(service: Any, args: Args) -> Any:
    return service.media_get(args.ident("media_id"))


def _h_inspect_media(service: Any, args: Args) -> Any:
    return service.inspect_media(args.string("ref"))


def _h_describe_media(service: Any, args: Args) -> Any:
    include = args.strings("include") or None
    return service.describe_media(args.string("ref"), include=include)


def _h_media_loudness(service: Any, args: Args) -> Any:
    return service.media_loudness(
        args.string("ref"), args.number_or("target_lufs", -14.0)
    )


def _h_media_silence(service: Any, args: Args) -> Any:
    return service.media_silence(
        args.string("ref"),
        args.number_or("threshold_db", -32.0),
        args.number_or("min_seconds", 0.35),
    )


def _h_media_scene_cuts(service: Any, args: Args) -> Any:
    return service.media_scene_cuts(
        args.string("ref"), args.number_or("threshold", 30.0)
    )


def _h_media_palette(service: Any, args: Args) -> Any:
    return service.media_palette(args.string("ref"), args.integer("count", 5))


def _h_media_contact_sheet(service: Any, args: Args) -> Any:
    return service.media_contact_sheet(
        args.string("ref"), args.integer("count", 9), args.integer("columns", 3)
    )


def _h_music_beat_grid(service: Any, args: Args) -> Any:
    return service.music_beat_grid(args.string("ref"), args.number("bpm"))


# --- Cutting ------------------------------------------------------------------


def _h_cut_media(service: Any, args: Args) -> Any:
    return service.cut_media(
        args.string("ref"),
        args.number_or("start_seconds", 0.0),
        args.number_or("end_seconds", 0.0),
        reencode=args.boolean("reencode", False),
    )


def _h_split_media(service: Any, args: Args) -> Any:
    return service.split_media(
        args.string("ref"),
        args.numbers("timestamps"),
        prefix=args.string("prefix", "clip"),
    )


def _h_join_media(service: Any, args: Args) -> Any:
    return service.join_media(
        args.strings("refs"), reencode=args.boolean("reencode", False)
    )


def _h_extract_audio_track(service: Any, args: Args) -> Any:
    return service.extract_audio_track(args.string("ref"), args.string("format", "mp3"))


def _h_extract_frame_image(service: Any, args: Args) -> Any:
    return service.extract_frame_image(
        args.string("ref"),
        args.number_or("at_seconds", 0.0),
        args.string("format", "png"),
    )


# --- Music and audio ----------------------------------------------------------


def _h_audio_trim(service: Any, args: Args) -> Any:
    return service.audio_trim(
        args.string("ref"),
        args.number_or("start_seconds", 0.0),
        args.number_or("end_seconds", 0.0),
        args.string("format", "mp3"),
    )


def _h_audio_fade(service: Any, args: Args) -> Any:
    return service.audio_fade(
        args.string("ref"),
        args.number_or("fade_in_seconds", 0.0),
        args.number_or("fade_out_seconds", 0.0),
        args.string("format", "mp3"),
    )


def _h_audio_loop(service: Any, args: Args) -> Any:
    return service.audio_loop(
        args.string("ref"),
        args.number_or("duration_seconds", 15.0),
        args.string("format", "mp3"),
    )


def _h_audio_normalize(service: Any, args: Args) -> Any:
    return service.audio_normalize(
        args.string("ref"),
        args.number_or("target_lufs", -14.0),
        args.string("format", "mp3"),
    )


def _h_audio_retime(service: Any, args: Args) -> Any:
    return service.audio_retime(
        args.string("ref"), args.number_or("factor", 1.0), args.string("format", "mp3")
    )


def _h_audio_mix(service: Any, args: Args) -> Any:
    duration = args.number("duration_seconds")
    return service.audio_mix(
        args.objects("tracks"),
        duration_seconds=duration,
        duck=args.boolean("duck", True),
        duck_db=args.number_or("duck_db", -12.0),
        format=args.string("format", "mp3"),
    )


# --- Image composition --------------------------------------------------------


def _h_compose_images(service: Any, args: Args) -> Any:
    return service.compose_images(
        args.string("base"), args.objects("layers"), args.string("format", "png")
    )


def _h_collage_images(service: Any, args: Args) -> Any:
    captions = args.strings("captions") or None
    return service.collage_images(
        args.strings("refs"),
        columns=args.integer("columns", 2),
        captions=captions,
        format=args.string("format", "png"),
    )


def _h_auto_cut_to_beat(service: Any, args: Args) -> Any:
    """Read a track's tempo and beat-match the project timeline to it."""
    project_id = args.ident("project_id")
    grid = service.music_beat_grid(args.string("music_ref"))
    tempo = args.integer("bpm", int(round(float(grid.get("bpm") or 120.0))))
    project = service.apply_ai_assist(project_id, fit=True, beat=True, bpm=tempo)
    return {
        "project": project,
        "bpm": grid.get("bpm"),
        "beat_count": len(grid.get("beats", [])),
        "timeline": service.timeline_report(project_id),
    }


# --- SEO: score it, fix it, and prove the fix ---------------------------------


def _optional_int(args: Args, key: str) -> int | None:
    """Read an optional whole number, tolerating a float from JSON."""
    value = args.number(key)
    return None if value is None else int(value)


def _h_seo_rules(service: Any, args: Args) -> Any:
    """Every threshold and signal weight the scorer uses, per platform."""
    return service.seo_rules()


def _h_seo_score(service: Any, args: Args) -> Any:
    """Score one publish pack, optionally on every platform at once."""
    return service.seo_score(
        args.choice("platform", SEO_PLATFORMS, "youtube"), args.mapping("pack")
    )


def _h_seo_optimize(service: Any, args: Args) -> Any:
    """Rewrite the pack for the best measurable score and report the gain."""
    return service.seo_optimize(
        args.choice("platform", SEO_PLATFORMS, "youtube"), args.mapping("pack")
    )


def _h_seo_score_project(service: Any, args: Args) -> Any:
    """Score what a stored project would actually publish, not a hypothetical."""
    return service.seo_score_project(
        args.ident("project_id"),
        args.choice("platform", SEO_PLATFORMS, "youtube"),
        keywords=args.strings("keywords") or None,
        publish_hour=_optional_int(args, "publish_hour"),
        audience_hours=[int(hour) for hour in args.numbers("audience_hours")],
        description=args.optional_string("description"),
        tags=args.strings("tags"),
        hashtags=args.strings("hashtags"),
        title=args.optional_string("title"),
        engagement=args.mapping("engagement") or None,
    )


def _h_seo_ab_plan(service: Any, args: Args) -> Any:
    """Size an A/B test: how much traffic a real decision needs."""
    return service.seo_ab_plan(
        args.choice("metric", SEO_METRICS, "ctr"),
        args.number_or("baseline_rate", 0.04),
        relative_lift=args.number_or("relative_lift", 0.15),
        daily_traffic=_optional_int(args, "daily_traffic"),
        arms=args.integer("arms", 2),
        alpha=args.number_or("alpha", 0.05),
        power=args.number_or("power", 0.8),
    )


def _h_seo_ab_evaluate(service: Any, args: Args) -> Any:
    """Decide whether a variant really beat the control, or it was noise."""
    arms = args.objects("arms")
    if len(arms) < 2:
        raise ToolError("Argument 'arms' needs at least two variants to compare.")
    return service.seo_ab_evaluate(
        args.choice("metric", SEO_METRICS, "ctr"),
        arms,
        alpha=args.number_or("alpha", 0.05),
        relative_lift=args.number_or("relative_lift", 0.15),
    )


def _h_seo_keywords(service: Any, args: Args) -> Any:
    """Rank phrases by demand vs competition and mine winning phrasings."""
    keywords = args.strings("keywords")
    if not keywords:
        raise ToolError("Argument 'keywords' needs at least one phrase.")
    return service.seo_keywords(
        keywords, args.objects("competitors"), pack=args.mapping("pack") or None
    )


def _h_seo_calibrate(service: Any, args: Args) -> Any:
    """Learn which signals actually predict this channel's outcomes."""
    observations = [
        (dict(row.get("signals") or {}), float(row.get("outcome") or 0.0))
        for row in args.objects("observations")
    ]
    return service.seo_calibrate(
        observations,
        args.choice("platform", _CALIBRATION_PLATFORMS, "youtube"),
        outcome=args.string("outcome", "views_per_day"),
    )


# ---------------------------------------------------------------------------
# The registry
# ---------------------------------------------------------------------------

_DISCOVERY: list[ToolSpec] = [
    ToolSpec(
        "list_projects",
        "List every content project with id, name, status and topic.",
        "discovery",
        "list_projects",
        _h_list_projects,
    ),
    ToolSpec(
        "get_project",
        "Read one project in full: script, research, timeline, grounding.",
        "discovery",
        "get_project",
        _h_get_project,
        {"project_id": PROJECT},
        ("project_id",),
    ),
    ToolSpec(
        "agent_catalog",
        "Which AI providers are configured, which script styles exist.",
        "discovery",
        "agent_catalog",
        _h_agent_catalog,
    ),
    ToolSpec(
        "list_script_styles",
        "Every scripting preset with its structure and constraints.",
        "discovery",
        "list_script_styles",
        _h_list_script_styles,
    ),
    ToolSpec(
        "list_media",
        "List the universal media library (id, kind, duration, transcript size).",
        "discovery",
        "media_list",
        _h_list_media,
    ),
    ToolSpec(
        "get_media",
        "Read one media item, including its transcript or extracted text.",
        "discovery",
        "media_get",
        _h_get_media,
        {"media_id": _p("string", "Media id from list_media.")},
        ("media_id",),
    ),
]

_RESEARCH: list[ToolSpec] = [
    ToolSpec(
        "create_project",
        "Create a project: name, topic, language, target duration.",
        "research",
        "create_project",
        _h_create_project,
        {
            "name": _p("string", "Working title."),
            "topic": _p("string", "What the video is about."),
            "target_language": _p("string", "BCP-47-ish code, 'vi' by default."),
            "duration_target_seconds": _p("integer", "Target runtime in seconds."),
        },
        ("name", "topic"),
    ),
    ToolSpec(
        "research_project",
        "Gather web sources and key facts for the project's topic.",
        "research",
        "research",
        _h_research_project,
        {
            "project_id": PROJECT,
            "include_web": _p("boolean", "Also query the federated web search."),
        },
        ("project_id",),
    ),
    ToolSpec(
        "list_kbs",
        "List knowledge bases (RAGFlow-style) with chunk counts.",
        "research",
        "list_kbs",
        _h_list_kbs,
    ),
    ToolSpec(
        "attach_kb",
        "Attach a knowledge base to a project (or detach with null).",
        "research",
        "attach_kb",
        _h_attach_kb,
        {
            "project_id": PROJECT,
            "kb_id": _p("string|null", "Knowledge base id, or null to detach."),
        },
        ("project_id",),
    ),
    ToolSpec(
        "ground_project",
        "Retrieve knowledge for the topic and bind citations [n] to the script.",
        "research",
        "ground_project",
        _h_ground_project,
        {"project_id": PROJECT},
        ("project_id",),
    ),
]

_SCRIPT: list[ToolSpec] = [
    ToolSpec(
        "export_brief",
        "Markdown brief for the project: context, contract, diagnostics.",
        "script",
        "export_brief",
        _h_export_brief,
        {"project_id": PROJECT},
        ("project_id",),
    ),
    ToolSpec(
        "update_script",
        "Save a narration script (with [Hook]/[Turn]/... section markers).",
        "script",
        "update_script",
        _h_update_script,
        {
            "project_id": PROJECT,
            "script": _p("string", "Narration script; blank lines separate sections."),
            "source_rights_confirmed": _p(
                "boolean", "Only a human may assert rights; leave false."
            ),
        },
        ("project_id", "script"),
    ),
    ToolSpec(
        "analyze_script",
        "Plan and lint the script: timing, hook strength, copy risk.",
        "script",
        "analyze_project_script",
        _h_analyze_script,
        {"project_id": PROJECT},
        ("project_id",),
    ),
]

_TIMELINE: list[ToolSpec] = [
    ToolSpec(
        "build_video_project",
        "Turn the approved script into an editable scene timeline.",
        "timeline",
        "build_video_project",
        _h_build_video_project,
        {"project_id": PROJECT},
        ("project_id",),
    ),
    ToolSpec(
        "timeline_report",
        "Score 0-100 plus issues: contrast, dead air, cut pace, overflow.",
        "timeline",
        "timeline_report",
        _h_timeline_report,
        {"project_id": PROJECT},
        ("project_id",),
    ),
    ToolSpec(
        "render_plan",
        "Absolute render plan: slots, caption cues, audio layers.",
        "timeline",
        "render_plan",
        _h_render_plan,
        {"project_id": PROJECT},
        ("project_id",),
    ),
    ToolSpec(
        "split_scene",
        "Split a scene in two at a fraction of its runtime.",
        "timeline",
        "split_video_scene",
        _h_split_scene,
        {
            "project_id": PROJECT,
            "scene_id": SCENE,
            "at": _p("number", "Split point as a fraction, 0.05..0.95."),
        },
        ("project_id", "scene_id"),
    ),
    ToolSpec(
        "merge_scene",
        "Merge a scene into the one that follows it.",
        "timeline",
        "merge_video_scene",
        _h_merge_scene,
        {"project_id": PROJECT, "scene_id": SCENE},
        ("project_id", "scene_id"),
    ),
    ToolSpec(
        "duplicate_scene",
        "Duplicate a scene right after it.",
        "timeline",
        "duplicate_video_scene",
        _h_duplicate_scene,
        {"project_id": PROJECT, "scene_id": SCENE},
        ("project_id", "scene_id"),
    ),
    ToolSpec(
        "delete_scene",
        "Delete a scene (the last remaining scene is protected).",
        "timeline",
        "delete_video_scene",
        _h_delete_scene,
        {"project_id": PROJECT, "scene_id": SCENE},
        ("project_id", "scene_id"),
    ),
    ToolSpec(
        "move_scene",
        "Reorder a scene to another index.",
        "timeline",
        "move_video_scene",
        _h_move_scene,
        {
            "project_id": PROJECT,
            "scene_id": SCENE,
            "to_index": _p("integer", "Zero-based destination index."),
        },
        ("project_id", "scene_id"),
    ),
    ToolSpec(
        "set_scene_speed",
        "Retime a scene: 0.5x slow motion .. 2x fast forward.",
        "timeline",
        "set_scene_speed",
        _h_set_scene_speed,
        {
            "project_id": PROJECT,
            "scene_id": SCENE,
            "speed": _p("number", "0.5..2.0 playback rate."),
        },
        ("project_id", "scene_id"),
    ),
    ToolSpec(
        "reverse_scene",
        "Play a scene's media backwards (boomerang).",
        "timeline",
        "reverse_scene",
        _h_reverse_scene,
        {
            "project_id": PROJECT,
            "scene_id": SCENE,
            "reverse": _p("boolean", "True to play in reverse."),
        },
        ("project_id", "scene_id"),
    ),
    ToolSpec(
        "trim_scene",
        "Set a scene's source in/out points in seconds.",
        "timeline",
        "trim_scene",
        _h_trim_scene,
        {
            "project_id": PROJECT,
            "scene_id": SCENE,
            "trim_start": _p("number", "Seconds into the source, or omit."),
            "trim_end": _p("number", "Seconds into the source, or omit."),
        },
        ("project_id", "scene_id"),
    ),
    ToolSpec(
        "set_scene_audio",
        "Scene audio: volume 0..2 plus fade in/out seconds.",
        "timeline",
        "set_scene_audio",
        _h_set_scene_audio,
        {
            "project_id": PROJECT,
            "scene_id": SCENE,
            "volume": _p("number", "0..2 gain for this clip."),
            "fade_in": _p("number", "Fade-in seconds."),
            "fade_out": _p("number", "Fade-out seconds."),
        },
        ("project_id", "scene_id"),
    ),
    ToolSpec(
        "bulk_update_scenes",
        "Apply one look (grade, filter, transition, ...) to many scenes.",
        "timeline",
        "bulk_update_video_scenes",
        _h_bulk_update_scenes,
        {
            "project_id": PROJECT,
            "scene_ids": _p("array", "Scene ids to patch.", items=SCENE),
            "patch": TIMELINE_PATCH,
        },
        ("project_id", "scene_ids", "patch"),
    ),
    ToolSpec(
        "set_keyframes",
        "Replace a scene's motion keyframe track.",
        "timeline",
        "set_scene_keyframes",
        _h_set_keyframes,
        {
            "project_id": PROJECT,
            "scene_id": SCENE,
            "keyframes": _p(
                "array",
                "Keyframes: {at, scale, x, y, rotation, opacity, easing}.",
                items=_p("object", "One keyframe."),
            ),
        },
        ("project_id", "scene_id", "keyframes"),
    ),
    ToolSpec(
        "add_marker",
        "Add a labelled timeline marker at a given second.",
        "timeline",
        "add_timeline_marker",
        _h_add_marker,
        {
            "project_id": PROJECT,
            "time_seconds": _p("number", "Marker position on the timeline."),
            "label": _p("string", "Short label, e.g. 'beat drop'."),
            "color": _p("string", "Hex colour, default #f59e0b."),
        },
        ("project_id", "time_seconds", "label"),
    ),
    ToolSpec(
        "ai_assist",
        "Auto-fit durations to narration and beat-match the cut to a BPM.",
        "timeline",
        "apply_ai_assist",
        _h_ai_assist,
        {
            "project_id": PROJECT,
            "fit": _p("boolean", "Stretch scenes to the narration length."),
            "beat": _p("boolean", "Snap cut points to the beat grid."),
            "bpm": _p("integer", "Tempo to match; use music_beat_grid to find it."),
        },
        ("project_id",),
    ),
    ToolSpec(
        "auto_cut_to_beat",
        "Read a music asset's tempo and beat-match the whole timeline to it.",
        "timeline",
        "media_beat_cut",
        _h_auto_cut_to_beat,
        {
            "project_id": PROJECT,
            "music_ref": REF,
            "bpm": _p("integer", "Override the detected tempo."),
        },
        ("project_id", "music_ref"),
    ),
]

_MEDIA: list[ToolSpec] = [
    ToolSpec(
        "inspect_media",
        "Technical fingerprint of a file: duration, streams, codecs, fps, size.",
        "media",
        "inspect_media",
        _h_inspect_media,
        {"ref": REF},
        ("ref",),
    ),
    ToolSpec(
        "describe_media",
        "Read a file without eyes: loudness, silence, shot changes, palette, "
        "tempo, on-screen text. The starting point for any media decision.",
        "media",
        "describe_media",
        _h_describe_media,
        {
            "ref": REF,
            "include": _p(
                "array",
                "Subset of loudness|silence|cuts|palette|beats|text (default: all).",
                items=_p("string", "Section name."),
            ),
        },
        ("ref",),
    ),
    ToolSpec(
        "media_loudness",
        "EBU R128 integrated loudness, true peak, and gain needed to hit target.",
        "media",
        "media_loudness",
        _h_media_loudness,
        {
            "ref": REF,
            "target_lufs": _p("number", "Delivery target, -14 LUFS by default."),
        },
        ("ref",),
    ),
    ToolSpec(
        "media_silence",
        "Silent gaps with timestamps, so a take can be tightened without listening.",
        "media",
        "media_silence",
        _h_media_silence,
        {
            "ref": REF,
            "threshold_db": _p("number", "Level below which audio counts as silent."),
            "min_seconds": _p("number", "Shortest gap to report."),
        },
        ("ref",),
    ),
    ToolSpec(
        "media_scene_cuts",
        "Shot boundaries with timestamps (histogram method, no vision model).",
        "media",
        "media_scene_cuts",
        _h_media_scene_cuts,
        {
            "ref": REF,
            "threshold": _p("number", "Higher means fewer, stronger cuts."),
        },
        ("ref",),
    ),
    ToolSpec(
        "media_palette",
        "Dominant colours as hex, so a look can be described and reused.",
        "media",
        "media_palette",
        _h_media_palette,
        {"ref": REF, "count": _p("integer", "How many colours to return.")},
        ("ref",),
    ),
    ToolSpec(
        "media_contact_sheet",
        "One image with evenly spaced frames plus their timestamps.",
        "media",
        "media_contact_sheet",
        _h_media_contact_sheet,
        {
            "ref": REF,
            "count": _p("integer", "How many frames to sample."),
            "columns": _p("integer", "Grid columns."),
        },
        ("ref",),
    ),
    ToolSpec(
        "cut_media",
        "Cut one time range out of any media file into a new asset.",
        "media",
        "cut_media",
        _h_cut_media,
        {
            "ref": REF,
            "start_seconds": _p(
                "number", "Range start; omit to cut from the beginning."
            ),
            "end_seconds": _p("number", "Range end."),
            "reencode": _p("boolean", "Force a frame-accurate re-encode."),
        },
        ("ref", "end_seconds"),
    ),
    ToolSpec(
        "split_media",
        "Cut one file at every timestamp into numbered clips.",
        "media",
        "split_media",
        _h_split_media,
        {
            "ref": REF,
            "timestamps": _p(
                "array", "Cut points in seconds.", items=_p("number", "Seconds.")
            ),
            "prefix": _p("string", "Filename prefix for the clips."),
        },
        ("ref", "timestamps"),
    ),
    ToolSpec(
        "join_media",
        "Join clips in order into one asset.",
        "media",
        "join_media",
        _h_join_media,
        {
            "refs": _p("array", "Assets to join, in order.", items=REF),
            "reencode": _p("boolean", "Re-encode instead of stream copy."),
        },
        ("refs",),
    ),
    ToolSpec(
        "extract_audio_track",
        "Pull the soundtrack out of a video into an audio asset.",
        "media",
        "extract_audio_track",
        _h_extract_audio_track,
        {"ref": REF, "format": _p("string", "mp3 (default) or wav.")},
        ("ref",),
    ),
    ToolSpec(
        "extract_frame_image",
        "Save a single frame as an image asset.",
        "media",
        "extract_frame_image",
        _h_extract_frame_image,
        {
            "ref": REF,
            "at_seconds": _p("number", "Timestamp to grab."),
            "format": _p("string", "png (default), jpeg, webp."),
        },
        ("ref",),
    ),
]

_AUDIO: list[ToolSpec] = [
    ToolSpec(
        "music_beat_grid",
        "Tempo plus beat and downbeat timestamps — the input to cutting on music.",
        "audio",
        "music_beat_grid",
        _h_music_beat_grid,
        {
            "ref": REF,
            "bpm": _p("number", "Override tempo detection."),
        },
        ("ref",),
    ),
    ToolSpec(
        "audio_trim",
        "Trim an audio asset to a range.",
        "audio",
        "audio_trim",
        _h_audio_trim,
        {
            "ref": REF,
            "start_seconds": _p(
                "number", "Range start; omit to trim from the beginning."
            ),
            "end_seconds": _p("number", "Range end."),
            "format": _p("string", "Output format, mp3 by default."),
        },
        ("ref", "end_seconds"),
    ),
    ToolSpec(
        "audio_fade",
        "Fade an audio asset in, out, or both.",
        "audio",
        "audio_fade",
        _h_audio_fade,
        {
            "ref": REF,
            "fade_in_seconds": _p("number", "Fade-in length."),
            "fade_out_seconds": _p("number", "Fade-out length."),
            "format": _p("string", "Output format, mp3 by default."),
        },
        ("ref",),
    ),
    ToolSpec(
        "audio_loop",
        "Loop a music bed until it reaches the requested length.",
        "audio",
        "audio_loop",
        _h_audio_loop,
        {
            "ref": REF,
            "duration_seconds": _p("number", "Target length."),
            "format": _p("string", "Output format, mp3 by default."),
        },
        ("ref", "duration_seconds"),
    ),
    ToolSpec(
        "audio_normalize",
        "Loudness-normalise to a streaming target, reporting before and after.",
        "audio",
        "audio_normalize",
        _h_audio_normalize,
        {
            "ref": REF,
            "target_lufs": _p("number", "Delivery target, -14 LUFS by default."),
            "format": _p("string", "Output format, mp3 by default."),
        },
        ("ref",),
    ),
    ToolSpec(
        "audio_retime",
        "Speed a track up or down without changing its pitch.",
        "audio",
        "audio_retime",
        _h_audio_retime,
        {
            "ref": REF,
            "factor": _p("number", "1.0 keeps the tempo; 1.25 is 25% faster."),
            "format": _p("string", "Output format, mp3 by default."),
        },
        ("ref", "factor"),
    ),
    ToolSpec(
        "audio_mix",
        "Mix several tracks (voice plus music bed) with per-track gain, offset, "
        "loop, and automatic ducking of the music under the voice.",
        "audio",
        "audio_mix",
        _h_audio_mix,
        {
            "tracks": AUDIO_TRACKS,
            "duration_seconds": _p("number", "Pad/limit the mix to this length."),
            "duck": _p("boolean", "Duck non-voice tracks under the voice track."),
            "duck_db": _p("number", "Ducking depth in dB."),
            "format": _p("string", "Output format, mp3 by default."),
        },
        ("tracks",),
    ),
]

_IMAGE: list[ToolSpec] = [
    ToolSpec(
        "image_presets",
        "List named photo looks (thumbnail, cinematic, noir) and available ops.",
        "image",
        "image_presets",
        _h_image_presets,
    ),
    ToolSpec(
        "edit_image",
        "Edit an image (base64) with an ops pipeline and/or a named preset.",
        "image",
        "edit_image",
        _h_edit_image,
        {
            "image_b64": _p("string", "Base64 of a png/jpeg/webp image."),
            "ops": _p(
                "array",
                "Ops: resize crop rotate flip tone curves color_balance filter "
                "vignette blur sharpen text padding auto_enhance remove_background.",
                items=_p("object", "{name, params}"),
            ),
            "preset": _p("string", "Named look, e.g. thumbnail."),
            "format": _p("string", "png, jpeg or webp."),
        },
        ("image_b64",),
    ),
    ToolSpec(
        "compose_images",
        "Composite images: place layers on a base with position, scale, opacity "
        "and blend mode — the 'gh\u00e9p \u1ea3nh' operator.",
        "image",
        "compose_images",
        _h_compose_images,
        {
            "base": REF,
            "layers": IMAGE_LAYERS,
            "format": _p("string", "png (default), jpeg, webp."),
        },
        ("base", "layers"),
    ),
    ToolSpec(
        "collage_images",
        "Grid several images into one sheet, with optional captions per cell.",
        "image",
        "collage_images",
        _h_collage_images,
        {
            "refs": _p("array", "Images to place, in order.", items=REF),
            "columns": _p("integer", "Grid columns."),
            "captions": _p(
                "array", "Caption per cell, same order as refs.", items=_p("string", "")
            ),
            "format": _p("string", "png (default), jpeg, webp."),
        },
        ("refs",),
    ),
]

_VOICE: list[ToolSpec] = [
    ToolSpec(
        "voice_presets",
        "List named voice chains (podcast, voiceover, soft) and their params.",
        "voice",
        "voice_presets",
        _h_voice_presets,
    ),
    ToolSpec(
        "enhance_voice",
        "Enhance raw voice audio (base64) with the Audition-style chain: "
        "highpass, gate, de-ess, 3-band EQ, compressor, loudness, reverb.",
        "voice",
        "process_voice_audio",
        _h_enhance_voice,
        {
            "audio_b64": _p("string", "Base64 of wav/mp3 audio."),
            "params": _p("object", "Chain overrides, e.g. {target_lufs: -16}."),
            "preset": _p("string", "Named chain, e.g. podcast."),
            "format": _p("string", "mp3 or wav."),
        },
        ("audio_b64",),
    ),
    ToolSpec(
        "duck_music",
        "Mix a music bed (base64) under a voice track (base64) with automatic "
        "sidechain ducking.",
        "voice",
        "duck_music_under_voice",
        _h_duck_music,
        {
            "voice_b64": _p("string", "Base64 voice track."),
            "music_b64": _p("string", "Base64 music bed."),
            "duck_db": _p("number", "Ducking depth in dB."),
        },
        ("voice_b64", "music_b64"),
    ),
]

_PRODUCTION: list[ToolSpec] = [
    ToolSpec(
        "render_video",
        "Export local timeline visuals and narration/music; never approve or publish. "
        "No embedded source audio, trim_end, reverse, or animated effects. "
        "audio_ref replaces narration/music with a finished mix.",
        "production",
        "render_video",
        _h_render_video,
        {
            "project_id": PROJECT,
            "export_format": _p(
                "string", "Container.", enum=["webm", "mp4"], default="webm"
            ),
            "audio_ref": REF,
        },
        ("project_id",),
    ),
    ToolSpec(
        "generate_voiceover",
        "Synthesize narration audio tracks for the timeline.",
        "production",
        "generate_voiceover",
        _h_generate_voiceover,
        {"project_id": PROJECT},
        ("project_id",),
    ),
    ToolSpec(
        "start_generation",
        "Render/export the video with the configured worker.",
        "production",
        "start_generation",
        _h_start_generation,
        {"project_id": PROJECT},
        ("project_id",),
    ),
    ToolSpec(
        "approve_stage",
        "Record a human approval gate (script or video).",
        "production",
        "approve",
        _h_approve_stage,
        {
            "project_id": PROJECT,
            "stage": _p("string", "'script' or 'video'."),
            "verdict": _p("string", "'approved' or 'rejected'."),
            "comment": _p("string", "Optional reviewer note."),
        },
        ("project_id", "stage"),
    ),
    ToolSpec(
        "publish_project",
        "Mark the finished video as published to the given platforms.",
        "production",
        "publish",
        _h_publish_project,
        {
            "project_id": PROJECT,
            "platforms": _p(
                "array", "Target platforms.", items=_p("string", "Platform.")
            ),
        },
        ("project_id",),
    ),
]

_SEO: list[ToolSpec] = [
    ToolSpec(
        "seo_rules",
        "Every platform threshold and signal weight the SEO scorer uses, so an "
        "agent reasons from the same numbers instead of guessing at them.",
        "seo",
        "seo_rules",
        _h_seo_rules,
    ),
    ToolSpec(
        "seo_score",
        "Score a publish pack 0-100 for youtube, youtube_shorts, tiktok or all: "
        "blocking issues, per-dimension breakdown, quick wins and confidence.",
        "seo",
        "seo_score",
        _h_seo_score,
        {"platform": _PLATFORM, "pack": PACK},
        ("pack",),
    ),
    ToolSpec(
        "seo_optimize",
        "Rewrite a pack for the maximum score and return the measured gain, so "
        "the fix is verified rather than assumed.",
        "seo",
        "seo_optimize",
        _h_seo_optimize,
        {"platform": _PLATFORM, "pack": PACK},
        ("pack",),
    ),
    ToolSpec(
        "seo_score_project",
        "Score what a stored project would actually publish: hook from the "
        "script, runtime, aspect, caption state, chapters, cut rate and audio.",
        "seo",
        "seo_score_project",
        _h_seo_score_project,
        {
            "project_id": PROJECT,
            "platform": _PLATFORM,
            "keywords": _p("array", "Target phrases, first one is primary."),
            "title": _p("string", "Override the project title."),
            "description": _p("string", "Override the description."),
            "tags": _p("array", "Tag list to score."),
            "hashtags": _p("array", "Hashtag list to score."),
            "publish_hour": _p("integer", "Planned local publish hour 0-23."),
            "audience_hours": _p("array", "Hours your audience is active."),
            "engagement": _p(
                "object",
                "Real metrics once published: views, impressions, likes, "
                "comments, shares, saves, follows, watch_time_seconds, "
                "average_view_seconds, completion_rate.",
            ),
        },
        ("project_id",),
    ),
    ToolSpec(
        "seo_ab_plan",
        "Size an A/B test for a detectable lift: sample per arm, calendar days "
        "at your traffic, and the decision rule.",
        "seo",
        "seo_ab_plan",
        _h_seo_ab_plan,
        {
            "metric": _METRIC,
            "baseline_rate": _p("number", "Current rate, e.g. 0.04 for 4% CTR."),
            "relative_lift": _p("number", "Lift to detect, 0.15 = +15%."),
            "daily_traffic": _p("integer", "Impressions/views per day available."),
            "arms": _p("integer", "Number of variants 2-6."),
            "alpha": _p("number", "Significance level, default 0.05."),
            "power": _p("number", "Power, default 0.8."),
        },
        ("baseline_rate",),
    ),
    ToolSpec(
        "seo_ab_evaluate",
        "Test whether a variant really beat the control: p-value, confidence "
        "interval, lift and a ship/keep-testing verdict.",
        "seo",
        "seo_ab_evaluate",
        _h_seo_ab_evaluate,
        {
            "metric": _METRIC,
            "arms": _p(
                "array",
                "2+ arms: name, impressions, clicks, views, completions, saves, "
                "shares, follows, watch_time_seconds, mean_value, sd_value.",
            ),
            "alpha": _p("number", "Significance level, default 0.05."),
            "relative_lift": _p("number", "Lift you would act on."),
        },
        ("arms",),
    ),
    ToolSpec(
        "seo_keywords",
        "Rank phrases by demand versus competition and mine the winning "
        "phrasings, using an optional competitor corpus.",
        "seo",
        "seo_keywords",
        _h_seo_keywords,
        {
            "keywords": _p("array", "Candidate phrases to rank."),
            "competitors": _p(
                "array",
                "Niche corpus rows: title, views, channel, subscribers, "
                "days_old, duration_seconds.",
            ),
            "pack": PACK,
        },
        ("keywords",),
    ),
    ToolSpec(
        "seo_calibrate",
        "Correlate each signal with this channel's real outcomes and suggest "
        "weights fitted to your own data instead of generic averages.",
        "seo",
        "seo_calibrate",
        _h_seo_calibrate,
        {
            "observations": _p("array", "Rows of {signals: {...}, outcome: number}."),
            "platform": _p(
                "string",
                "youtube, youtube_shorts or tiktok.",
                enum=list(_CALIBRATION_PLATFORMS),
                default="youtube",
            ),
            "outcome": _p("string", "What you are predicting."),
        },
        ("observations",),
    ),
]

#: Every tool, in the order agents should discover them.
TOOL_SPECS: list[ToolSpec] = [
    *_DISCOVERY,
    *_RESEARCH,
    *_SCRIPT,
    *_TIMELINE,
    *_MEDIA,
    *_AUDIO,
    *_IMAGE,
    *_VOICE,
    *_SEO,
    *_PRODUCTION,
]

TOOL_REGISTRY: dict[str, ToolSpec] = {spec.name: spec for spec in TOOL_SPECS}

#: Public, JSON-safe manifest (kept as a plain list for older readers).
TOOL_MANIFEST: list[dict[str, Any]] = [spec.manifest_entry() for spec in TOOL_SPECS]

_USAGE_NOTES = [
    "Workflow order: create_project -> research_project -> (attach_kb + "
    "ground_project) -> update_script -> analyze_script -> approve_stage(script) "
    "-> build_video_project -> timeline edits -> generate_voiceover -> "
    "start_generation -> approve_stage(video) -> publish_project.",
    "Scene ids are returned inside get_project / build_video_project responses.",
    "A script approval gate must pass before build_video_project works.",
    "All edits are validated server-side; errors describe the exact problem.",
    "Without vision, read before you cut: describe_media returns duration, "
    "loudness, silences, shot changes, palette and tempo as text.",
    "Media tools are chainable: every output carries an asset_id that any other "
    "media tool accepts as its ref, including in the same conversation.",
    "To cut on the music, call music_beat_grid (or auto_cut_to_beat) first, then "
    "split_media with the returned beat timestamps.",
    "For a narration-over-music bed, call audio_mix with one track marked "
    "role='voice' so the music ducks automatically.",
    "Only a human may confirm source rights or pass an approval gate; the tools "
    "record those decisions but never invent them.",
    "Before publishing: seo_score_project (or seo_score with a pack) to measure "
    "readiness, seo_optimize to get the rewrite and the measured gain, then "
    "seo_ab_plan before changing anything on a live channel.",
    "seo_score returns 'unknown' signals when a fact is not recorded; that is "
    "missing information, never a passing grade. Fill the field, do not guess it.",
    "After publishing, pass the real analytics back as 'engagement' so scores "
    "describe performance measured against targets, not just metadata hygiene.",
]


def build_tool_manifest() -> dict[str, Any]:
    """The GET /tools payload: schemas, categories, and usage notes."""
    return {
        "protocol": "content-factory-tools/1",
        "endpoint": "/tools/call",
        "schema": "json-schema/draft-07 (subset)",
        "count": len(TOOL_SPECS),
        "categories": sorted({spec.category for spec in TOOL_SPECS}),
        "tools": TOOL_MANIFEST,
        "usage_notes": _USAGE_NOTES,
    }


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


def dispatch_tool(service: Any, name: str, args: dict[str, Any] | None = None) -> Any:
    """Execute one tool by name with JSON args and return a JSON-safe result.

    Raises :class:`ToolError` for unknown tools and malformed arguments;
    domain errors from the service layer propagate unchanged so the API can map
    them to 404/409 the same way its own endpoints do.
    """
    spec = TOOL_REGISTRY.get(name)
    if spec is None:
        raise ToolError(
            f"Unknown tool '{name}'. GET /tools lists the {len(TOOL_SPECS)} available."
        )
    payload = dict(args or {})
    # The published schema must not lie: anything marked required is enforced
    # here, so a handler can never be reached with a missing argument.
    missing = [key for key in spec.required if payload.get(key) is None]
    if missing:
        raise ToolError(f"Missing required argument(s): {', '.join(missing)}.")
    return _serialize_result(spec.handler(service, Args(payload)))


def _serialize_result(value: Any) -> Any:
    """Convert service models nested in lists and mappings to JSON data."""
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_serialize_result(item) for item in value]
    if isinstance(value, tuple):
        return [_serialize_result(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize_result(item) for key, item in value.items()}
    return value
