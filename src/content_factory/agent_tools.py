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

The registry itself is only the assembly: the shared tool DSL lives in
``agent_schema`` and each domain (project, timeline, media, seo, plus audio,
video, photo, knowledge, youtube and compute) owns the handlers and the schemas
for its own tools.  This module fixes the order in which agents discover them.
"""

from __future__ import annotations

import inspect
import re
from dataclasses import replace
from typing import Any

from .agent_audio import audio_tool_specs
from .agent_compute import compute_tool_specs
from .agent_knowledge import knowledge_tool_specs
from .agent_media import AUDIO_SPECS, IMAGE_SPECS, MEDIA_SPECS, VOICE_SPECS
from .agent_photo import photo_tool_specs
from .agent_project import (
    DISCOVERY_SPECS,
    PRODUCTION_SPECS,
    RESEARCH_SPECS,
    SCRIPT_SPECS,
)
from .agent_schema import Args, ToolError, ToolSpec, _p
from .agent_seo import SEO_SPECS
from .agent_skills import SKILLS, Skill, read_skill, skill_index
from .agent_timeline import TIMELINE_SPECS
from .agent_video import video_tool_specs
from .agent_youtube import youtube_tool_specs
from .workflow import _run_sync

__all__ = [
    "TOOL_MANIFEST",
    "TOOL_REGISTRY",
    "Args",
    "ToolError",
    "ToolSpec",
    "build_tool_manifest",
    "dispatch_tool",
    "search_tools",
]


# ---------------------------------------------------------------------------
# Registry-level handlers (search, skills)
# ---------------------------------------------------------------------------


def _h_search_tools(service: Any, args: Args) -> Any:
    query = args.string("query")
    hits = search_tools(query, limit=args.integer("limit", 10))
    return {
        "query": query,
        "returned": len(hits),
        "tools": hits,
        "hint": (
            "Run one with POST /tools/call (tool=<name>, args={...}); "
            "GET /tools/<name> returns its full schema."
        ),
    }


def _h_list_skills(service: Any, args: Args) -> Any:
    return {
        "count": len(SKILLS),
        "skills": skill_index(),
        "hint": "Read one with read_skill to get its ordered steps.",
    }


def _h_read_skill(service: Any, args: Args) -> Any:
    name = args.string("name")
    skill: Skill | None = read_skill(name)
    if skill is None:
        raise ToolError(
            f"Unknown skill '{name}'. list_skills names the {len(SKILLS)} "
            f"available: {', '.join(skill.name for skill in SKILLS)}."
        )
    return skill.manifest_entry()


#: The registry's own tools: discover a tool, then read a recipe.  They come
#: first because an agent with a fixed tool budget (or a tool-search budget)
#: should be able to reach the rest of the catalog from here.
REGISTRY_SPECS: list[ToolSpec] = [
    ToolSpec(
        "search_tools",
        "Find the right tool for a job from a plain-language description.",
        "discovery",
        "agent_tools",
        _h_search_tools,
        {
            "query": _p("string", "What you are trying to do, in words."),
            "limit": _p("integer", "How many matches to return (default 10)."),
        },
        ("query",),
    ),
    ToolSpec(
        "list_skills",
        "List the step-by-step recipes agents follow: name, purpose and tools.",
        "discovery",
        "agent_skills",
        _h_list_skills,
        {},
        (),
    ),
    ToolSpec(
        "read_skill",
        "Read one full recipe: ordered steps, arguments, human gates, guardrails.",
        "discovery",
        "agent_skills",
        _h_read_skill,
        {"name": _p("string", "Skill name from list_skills.")},
        ("name",),
    ),
]


#: Every tool, in the order agents should discover them.
_RAW_SPECS: list[ToolSpec] = [
    *REGISTRY_SPECS,
    *DISCOVERY_SPECS,
    *compute_tool_specs(),
    *RESEARCH_SPECS,
    *knowledge_tool_specs(),
    *youtube_tool_specs(),
    *SCRIPT_SPECS,
    *TIMELINE_SPECS,
    *MEDIA_SPECS,
    *AUDIO_SPECS,
    *audio_tool_specs(),
    *IMAGE_SPECS,
    *photo_tool_specs(),
    *video_tool_specs(),
    *VOICE_SPECS,
    *SEO_SPECS,
    *PRODUCTION_SPECS,
]

#: The words a caller actually types, mapped onto the tool that does the job.
#: Written for search, not for reading: a catalog description is prose, while an
#: agent arrives with a sentence like "duck the music under the narration" and
#: needs ``audio_mix``.  Keys are checked against the registry by
#: ``tests/test_agent_discovery.py``, so this table cannot rot silently.
TOOL_KEYWORDS: dict[str, tuple[str, ...]] = {
    "describe_media": (
        "read a clip",
        "look inside",
        "watch",
        "without watching",
        "understand a video",
        "what is in this file",
    ),
    "inspect_media": ("metadata", "look inside", "what is in this file", "probe"),
    "media_contact_sheet": (
        "storyboard",
        "grid",
        "grid of frames",
        "thumbnail strip",
        "preview frames",
    ),
    "collage_images": ("grid", "sheet", "mosaic", "photo grid"),
    "media_loudness": ("volume", "how loud", "measure", "lufs", "level"),
    "analyze_audio": ("measure", "how loud", "spectrum", "analyse the audio"),
    "audio_mix": (
        "duck",
        "ducking",
        "narration",
        "voiceover",
        "mix voice and music",
    ),
    "duck_music": ("duck", "ducking", "narration under music", "lower the music"),
    "music_beat_grid": ("tempo", "bpm", "beat", "downbeat"),
    "split_media": ("beat", "cut on the beat", "slice", "montage"),
    "auto_cut_to_beat": ("beat", "montage", "cut to the music"),
    "seo_score": ("title", "tags", "packaging", "how good is the title"),
    "seo_score_project": ("title", "tags", "packaging", "publish readiness"),
    "apply_audio_mastering": ("finalize the mix", "polish", "master"),
}

#: Every tool with the search keywords attached.  ``dataclasses.replace`` keeps
#: the specs frozen while the table above stays the one place search words live.
TOOL_SPECS: list[ToolSpec] = [
    replace(spec, keywords=TOOL_KEYWORDS.get(spec.name, ())) for spec in _RAW_SPECS
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
    "Before a long export or transcription, call resource_explain (or "
    "resource_status) to see whether the GPU is free; heavy jobs are serialized "
    "on purpose so one laptop stays responsive.",
    "Before publishing: seo_score_project (or seo_score with a pack) to measure "
    "readiness, seo_optimize to get the rewrite and the measured gain, then "
    "seo_ab_plan before changing anything on a live channel.",
    "seo_score returns 'unknown' signals when a fact is not recorded; that is "
    "missing information, never a passing grade. Fill the field, do not guess it.",
    "After publishing, pass the real analytics back as 'engagement' so scores "
    "describe performance measured against targets, not just metadata hygiene.",
    "Do not pull every schema into context: search_tools (or GET /tools?q=...)"
    " finds the tool for the job, and GET /tools?detail=index is one line each.",
    "Long jobs have a documented order: list_skills (or GET /skills) returns the"
    " recipes, read_skill the ordered steps with the arguments they need.",
]


#: Words that carry no tool signal.  Without this, "read what is inside a video
#: without watching it" matched ``read_skill`` on "read" and ``edit_image`` on
#: "inside" — noise that buries the tools the caller actually meant.
_STOPWORDS = frozenset(
    """
    a about after all also am an and any are as at be because been before being
    both but by can cannot could did do does doing done down during each few for
    from further had has have having he her here hers him his how i if in into
    is it its itself just like me more most my no nor not now of off on once
    only or other our out over own same she should so some such than that the their
    them then there these they this those through to too under until up very
    was we were what when where which while who whom why will with without
    would you your
    """.split()
)


def search_tools(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Rank the catalog against a plain-language query.

    An agent asked to "make the music duck under the narration" should not have
    to read 113 schemas to find ``audio_mix``.  Names beat descriptions, exact
    terms beat partial ones, and a tool that declares the argument you mentioned
    gets a nudge — the same heuristics a person uses when skimming the list.
    """
    terms = [
        term
        for term in re.split(r"[^a-z0-9_]+", str(query).lower())
        if term and term not in _STOPWORDS
    ]
    if not terms:
        return []
    query_text = str(query).lower()
    scored = [(spec, _match_score(spec, terms, query_text)) for spec in TOOL_SPECS]
    hits = [pair for pair in scored if pair[1] > 0]
    hits.sort(key=lambda pair: (-pair[1], TOOL_SPECS.index(pair[0])))
    return [_index_entry(spec) for spec, _score in hits[: max(1, limit)]]


def _match_score(spec: ToolSpec, terms: list[str], query: str) -> int:
    """How well one tool matches one query.

    Three signals, in order of trust: the tool's own name, a synonym the catalog
    author listed for it, then loose word overlap.  Terms of three characters or
    fewer only count as whole words — substring matching made "one" a match for
    ``voice_clone``, which is how a search starts returning confident nonsense.
    """
    name = spec.name.lower()
    description = spec.description.lower()
    category = spec.category.lower()
    arguments = " ".join(key.lower() for key in spec.properties)
    haystack = f"{name} {description} {category} {arguments}"
    words = set(re.split(r"[^a-z0-9_]+", haystack))
    score = 0
    for term in terms:
        if term == name:
            score += 100
        elif len(term) > 3 and term in name:
            score += 40
        if term == category:
            score += 15
        if term in words:
            score += 20
        elif len(term) > 3 and term in description:
            score += 10
        if term in arguments:
            score += 5
    if any(phrase in query for phrase in spec.keywords):
        score += 50
    return score


def _index_entry(spec: ToolSpec) -> dict[str, Any]:
    """One line per tool: enough to choose it, without the JSON Schema."""
    return {
        "name": spec.name,
        "description": spec.description,
        "category": spec.category,
        "required": list(spec.required),
    }


def tool_spec(name: str) -> ToolSpec | None:
    """One tool's full spec, for ``GET /tools/{name}``."""
    return TOOL_REGISTRY.get(str(name).strip())


def build_tool_manifest(
    *,
    q: str | None = None,
    category: str | None = None,
    detail: str = "full",
    limit: int | None = None,
) -> dict[str, Any]:
    """The GET /tools payload: schemas, categories, usage notes, skills.

    ``detail="index"`` answers with one line per tool instead of every schema —
    the full manifest is a large slice of a context window for a job that needs
    three tools, and an agent that filters first spends its budget on the work.
    ``total`` and ``has_more`` are always present, so a caller can tell a short
    answer from a truncated one.
    """
    specs = [spec for spec in TOOL_SPECS if category in (None, spec.category)]
    if q:
        matched = {entry["name"] for entry in search_tools(q, len(TOOL_SPECS))}
        specs = [spec for spec in specs if spec.name in matched]
    total = len(specs)
    if limit is not None and limit >= 0:
        specs = specs[:limit]
    indexed = detail == "index"
    return {
        "protocol": "content-factory-tools/1",
        "endpoint": "/tools/call",
        "schema": "json-schema/draft-07 (subset)",
        "count": len(TOOL_SPECS),
        "returned": len(specs),
        "total": total,
        "has_more": len(specs) < total,
        "detail": "index" if indexed else "full",
        "categories": sorted({spec.category for spec in TOOL_SPECS}),
        "skills_endpoint": "/skills",
        "tools": [
            _index_entry(spec) if indexed else spec.manifest_entry() for spec in specs
        ],
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
        closest = search_tools(name, limit=3)
        hint = (
            " Closest matches: " + ", ".join(entry["name"] for entry in closest) + "."
            if closest
            else " Call search_tools with a description of the job to find one."
        )
        raise ToolError(
            f"Unknown tool '{name}'. GET /tools lists the {len(TOOL_SPECS)} "
            f"available.{hint}"
        )
    payload = dict(args or {})
    # The published schema must not lie: anything marked required is enforced
    # here, so a handler can never be reached with a missing argument.
    missing = [key for key in spec.required if payload.get(key) is None]
    if missing:
        raise ToolError(
            f"Missing required argument(s): {', '.join(missing)}. "
            f"GET /tools/{name} shows the schema; search_tools finds related tools."
        )
    return _serialize_result(spec.handler(service, Args(payload)))


def _serialize_result(value: Any) -> Any:
    """Convert service models nested in lists and mappings to JSON data.

    An awaitable is driven to completion first: a sync handler that calls an
    async service method returns a bare coroutine unless it bridges the two,
    and that used to reach the response layer and fail there as an opaque 500
    (``research_project`` did exactly that, for months). Handlers still bridge
    their own coroutines — this is the safety net under the last one.
    """
    if inspect.isawaitable(value):
        return _serialize_result(_run_sync(value))
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_serialize_result(item) for item in value]
    if isinstance(value, tuple):
        return [_serialize_result(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize_result(item) for key, item in value.items()}
    return value
