"""Project-lifecycle agent tools: discovery, research, script, production.

Split out of ``agent_tools.py`` so the registry module holds only the assembly
of the manifest, while each domain keeps its handlers next to the schemas that
describe them.  The tool order in the manifest is set by ``agent_tools``; this
module only defines the specs, it does not decide where they appear.
"""

from __future__ import annotations

from typing import Any

from .agent_schema import PROJECT, REF, Args, ToolSpec, _p
from .models import (
    ApprovalCreate,
    ApprovalStage,
    ApprovalVerdict,
    GroundRequest,
    ProjectCreate,
    PublishCreate,
    ScriptAnalyzeRequest,
    ScriptUpdate,
)
from .workflow import _run_sync

# ---------------------------------------------------------------------------
# Handlers — one small function per tool
# ---------------------------------------------------------------------------


def _h_list_projects(service: Any, args: Args) -> Any:
    return service.list_projects()


def _h_get_project(service: Any, args: Args) -> Any:
    return service.get_project(args.ident("project_id"))


def _h_agent_catalog(service: Any, args: Args) -> Any:
    return service.agent_catalog()


def _h_list_script_styles(service: Any, args: Args) -> Any:
    return service.list_script_styles()


def _h_list_media(service: Any, args: Args) -> Any:
    return service.media_list()


def _h_get_media(service: Any, args: Args) -> Any:
    return service.media_get(args.ident("media_id"))


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
    """Run a research pass.

    ``ServiceMixin.research`` is async (the federated searcher is), and a tool
    handler is sync, so the coroutine is driven to completion through the same
    bridge the other async tools use. Without it the handler returns a bare
    coroutine and the response fails to serialize.
    """
    return _run_sync(
        service.research(
            args.ident("project_id"), include_web=args.boolean("include_web", True)
        )
    )


def _h_list_kbs(service: Any, args: Args) -> Any:
    return service.list_kbs()


def _h_attach_kb(service: Any, args: Args) -> Any:
    return service.attach_kb(args.ident("project_id"), args.optional_ident("kb_id"))


def _h_ground_project(service: Any, args: Args) -> Any:
    """Retrieve knowledge for the topic and bind citations to the script."""
    return service.ground_project(
        args.ident("project_id"),
        GroundRequest(
            query=args.optional_string("query"),
            top_k=args.integer("top_k", 6),
        ),
    )


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


def _h_render_video(service: Any, args: Args) -> Any:
    return service.render_video(
        args.ident("project_id"),
        args.choice("export_format", ("webm", "mp4"), "webm"),
        args.optional_string("audio_ref"),
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


# ---------------------------------------------------------------------------
# Specs
# ---------------------------------------------------------------------------

DISCOVERY_SPECS: list[ToolSpec] = [
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

RESEARCH_SPECS: list[ToolSpec] = [
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
        {
            "project_id": PROJECT,
            "query": _p("string", "Optional retrieval query (defaults to the topic)."),
            "top_k": _p("integer", "How many chunks to retrieve (1-50)."),
        },
        ("project_id",),
    ),
]

SCRIPT_SPECS: list[ToolSpec] = [
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

PRODUCTION_SPECS: list[ToolSpec] = [
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
