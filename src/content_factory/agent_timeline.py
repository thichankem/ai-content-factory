"""Timeline (NLE) agent tools: build, inspect and edit the video project.

Split out of ``agent_tools.py`` so the registry module holds only the assembly
of the manifest, while the timeline domain keeps its handlers next to the
schemas that describe them.
"""

from __future__ import annotations

from typing import Any

from .agent_schema import PROJECT, REF, SCENE, TIMELINE_PATCH, Args, ToolSpec, _p

# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


def _h_build_video_project(service: Any, args: Args) -> Any:
    return service.build_video_project(args.ident("project_id"))


def _h_timeline_report(service: Any, args: Args) -> Any:
    return service.timeline_report(args.ident("project_id"))


def _h_render_plan(service: Any, args: Args) -> Any:
    return service.render_plan(args.ident("project_id"))


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


def _h_auto_cut_to_beat(service: Any, args: Args) -> Any:
    """Read a track's tempo and beat-match the project timeline to it."""
    project_id = args.ident("project_id")
    grid = service.music_beat_grid(args.string("music_ref"))
    tempo = args.integer("bpm", round(float(grid.get("bpm") or 120.0)))
    project = service.apply_ai_assist(project_id, fit=True, beat=True, bpm=tempo)
    return {
        "project": project,
        "bpm": grid.get("bpm"),
        "beat_count": len(grid.get("beats", [])),
        "timeline": service.timeline_report(project_id),
    }


# ---------------------------------------------------------------------------
# Specs
# ---------------------------------------------------------------------------

TIMELINE_SPECS: list[ToolSpec] = [
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
