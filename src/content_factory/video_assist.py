"""Accessibility layer for the video/audio editing engine.

Mirrors the photo accessibility layer: every operation a text-only agent (or a
screen reader) can drive is documented in plain language, a timeline is
described as a sentence, and the validator's findings become concrete edit
suggestions. This is what lets a non-vision user or an AI agent operate the
whole video pipeline without ever seeing a frame or hearing a clip.
"""

from __future__ import annotations

from typing import Any

from . import audio_effects, video_effects
from .catalog import detail, grouped_catalog
from .models import VideoProject

__all__ = [
    "catalog",
    "describe_operation",
    "describe_timeline",
    "suggest_edits",
]


#: The order categories appear in the catalogue; every one always appears, so a
#: client can render a stable menu even when a category is momentarily empty.
CATEGORY_ORDER = [
    "editing",
    "image",
    "effects",
    "text",
    "audio",
    "media",
    "motion",
    "export",
]


#: Plain-language docs for the timeline / media operations. Keys match the
#: operation names surfaced to agents and the UI.
OP_DOCS: dict[str, dict[str, Any]] = {
    # --- timeline / editing --------------------------------------------------
    "split_scene": {
        "category": "editing",
        "description": "Split one scene into two at a fraction of its runtime, "
        "dividing the text and narration between the halves.",
        "params": {
            "scene_id": "The scene to split.",
            "at": "Fraction 0..1 where to cut.",
        },
    },
    "merge_scene": {
        "category": "editing",
        "description": "Merge a scene into the following one (the reverse of a split).",
        "params": {"scene_id": "The scene to merge forward."},
    },
    "duplicate_scene": {
        "category": "editing",
        "description": "Insert a copy of a scene directly after it.",
        "params": {"scene_id": "The scene to duplicate."},
    },
    "delete_scene": {
        "category": "editing",
        "description": "Remove a scene (the last remaining scene is protected).",
        "params": {"scene_id": "The scene to delete."},
    },
    "move_scene": {
        "category": "editing",
        "description": "Reorder a scene to a new position on the timeline.",
        "params": {"scene_id": "The scene to move.", "to_index": "New position."},
    },
    "set_scene_speed": {
        "category": "editing",
        "description": "Retime a scene (0.5x slow-mo .. 2x fast-forward), shrinking "
        "or growing its timeline slot.",
        "params": {"scene_id": "The scene.", "speed": "Playback speed."},
    },
    "reverse_scene": {
        "category": "editing",
        "description": "Play a scene's source media backwards.",
        "params": {"scene_id": "The scene.", "reverse": "True to reverse."},
    },
    "trim_scene": {
        "category": "editing",
        "description": "Set a scene's source in/out handles without changing its "
        "timeline slot (NLE clip trim).",
        "params": {
            "scene_id": "The scene.",
            "trim_start": "In point (s).",
            "trim_end": "Out point (s).",
        },
    },
    "set_scene_audio": {
        "category": "editing",
        "description": "Adjust a scene's gain and audio fade in/out.",
        "params": {
            "scene_id": "The scene.",
            "volume": "Gain 0..2.",
            "fade_in": "Fade-in (s).",
            "fade_out": "Fade-out (s).",
        },
    },
    "set_keyframes": {
        "category": "editing",
        "description": "Replace a scene's motion keyframe track (scale, rotation, "
        "opacity, position over time).",
        "params": {"scene_id": "The scene.", "keyframes": "List of keyframe points."},
    },
    "add_marker": {
        "category": "editing",
        "description": "Add a labelled marker (beat, chapter, note) to the timeline.",
        "params": {
            "time_seconds": "Where on the timeline.",
            "label": "Marker text.",
            "color": "Marker colour.",
        },
    },
    "bulk_update_scenes": {
        "category": "editing",
        "description": "Apply the same look (filter, grade, effect, font…) to many "
        "scenes at once.",
        "params": {"scene_ids": "Scenes to update.", "patch": "Fields to set."},
    },
    "ai_assist": {
        "category": "editing",
        "description": "Auto-edit: fit scenes to the target duration and/or snap "
        "cuts to a music beat.",
        "params": {
            "fit": "Fit to target length.",
            "beat": "Snap to beats.",
            "bpm": "Beats per minute.",
        },
    },
    # --- image / colour ------------------------------------------------------
    "set_scene_filter": {
        "category": "image",
        "description": "Apply a one-click colour/treatment filter (grayscale, "
        "sepia, invert, blur, vignette, warm, cool, contrast, brightness).",
        "params": {"scene_id": "The scene.", "filter": "The filter name."},
    },
    "set_scene_grade": {
        "category": "image",
        "description": "Apply a cinematic colour grade (teal-orange, noir, "
        "vintage, cyberpunk, pastel).",
        "params": {"scene_id": "The scene.", "grade": "The grade name."},
    },
    "set_scene_effect": {
        "category": "image",
        "description": "Apply a visual effect overlay (glitch, pixelate, "
        "scanlines, film-grain, old-film, dreamy, sharpen, mosaic).",
        "params": {"scene_id": "The scene.", "effect": "The effect name."},
    },
    # --- effects -------------------------------------------------------------
    "set_scene_transition": {
        "category": "effects",
        "description": "Set how a scene blends in from the previous one (cut, "
        "fade, slide, zoom, wipe, circle, dissolve).",
        "params": {"scene_id": "The scene.", "transition": "The transition name."},
    },
    "set_scene_ken_burns": {
        "category": "effects",
        "description": "Pan/zoom a static background (pan-left, pan-right, "
        "zoom-in, zoom-out).",
        "params": {"scene_id": "The scene.", "ken_burns": "The motion preset."},
    },
    # --- text / graphics -----------------------------------------------------
    "set_scene_text": {
        "category": "text",
        "description": "Set a scene's on-screen text, position, colour, font "
        "size, style, and entrance/exit animation.",
        "params": {
            "scene_id": "The scene.",
            "text": "The text.",
            "text_style": "normal/title/subtitle/caption/neon/outline/shadow.",
        },
    },
    "set_scene_overlay": {
        "category": "text",
        "description": "Place an emoji/sticker overlay on a scene.",
        "params": {
            "scene_id": "The scene.",
            "overlay_emoji": "The emoji.",
            "overlay_pos": "Corner.",
            "overlay_size": "Size.",
        },
    },
    # --- audio ---------------------------------------------------------------
    "audio_trim": {
        "category": "audio",
        "description": "Trim an audio file to a range.",
        "params": {
            "ref": "Audio asset.",
            "start_seconds": "Start.",
            "end_seconds": "End.",
        },
    },
    "audio_fade": {
        "category": "audio",
        "description": "Apply fade in/out to an audio file.",
        "params": {
            "ref": "Audio asset.",
            "fade_in_seconds": "Fade-in.",
            "fade_out_seconds": "Fade-out.",
        },
    },
    "audio_loop": {
        "category": "audio",
        "description": "Loop a music bed until it reaches a target duration.",
        "params": {"ref": "Audio asset.", "duration_seconds": "Target length."},
    },
    "audio_normalize": {
        "category": "audio",
        "description": "Loudness-normalise to a streaming target (EBU R128).",
        "params": {"ref": "Audio asset.", "target_lufs": "Target loudness."},
    },
    "audio_retime": {
        "category": "audio",
        "description": "Speed a track up or down without changing pitch.",
        "params": {"ref": "Audio asset.", "factor": "Speed factor."},
    },
    "audio_mix": {
        "category": "audio",
        "description": "Mix several tracks with per-track gain, delay and "
        "optional voice-ducking of the music bus.",
        "params": {"tracks": "List of {path, gain_db, offset_seconds, role}."},
    },
    "music_beat_grid": {
        "category": "audio",
        "description": "Detect tempo and beat timestamps so cuts can land on the "
        "music.",
        "params": {"ref": "Music asset.", "bpm": "Optional known tempo."},
    },
    "enhance_voice": {
        "category": "audio",
        "description": "Enhance a voice track (denoise, eq, compression) through "
        "the Audition-style chain.",
        "params": {"audio_b64": "Voice audio.", "preset": "Named chain."},
    },
    "duck_music": {
        "category": "audio",
        "description": "Duck a music bed under a voice track.",
        "params": {
            "voice_b64": "Voice.",
            "music_b64": "Music.",
            "duck_db": "How much to duck.",
        },
    },
    # --- media reading -------------------------------------------------------
    "describe_media": {
        "category": "media",
        "description": "Describe a media file as text: duration, loudness, "
        "silences, shot changes, palette, tempo — so a non-vision agent can "
        "reason about it.",
        "params": {"ref": "Media id, edited asset id, or path."},
    },
    "inspect_media": {
        "category": "media",
        "description": "Technical probe of a media file (codecs, resolution, "
        "fps, channels).",
        "params": {"ref": "Media reference."},
    },
    "media_scene_cuts": {
        "category": "media",
        "description": "Detect shot boundaries as a list of segments.",
        "params": {"ref": "Video reference."},
    },
    "media_silence": {
        "category": "media",
        "description": "Find silent gaps in the audio.",
        "params": {"ref": "Media reference."},
    },
    "media_palette": {
        "category": "media",
        "description": "Dominant colours as hex strings.",
        "params": {"ref": "Media reference."},
    },
    # --- camera / motion -----------------------------------------------------
    "set_scene_motion": {
        "category": "motion",
        "description": "Animate a scene's scale, rotation, opacity and position "
        "over its runtime (single-segment motion).",
        "params": {"scene_id": "The scene.", "motion": "SceneMotion object."},
    },
    # --- export --------------------------------------------------------------
    "render_video": {
        "category": "export",
        "description": "Render the timeline to a real video file (webm or mp4).",
        "params": {"project_id": "The project.", "export_format": "webm or mp4."},
    },
    "render_plan": {
        "category": "export",
        "description": "Compile the timeline into an explicit render plan "
        "(absolute slots, captions, audio layers).",
        "params": {"project_id": "The project."},
    },
}


def _merge_effect_docs() -> dict[str, dict[str, Any]]:
    """Fold the frame/audio effect catalogs into the op docs."""
    merged = dict(OP_DOCS)
    for entry in video_effects.effect_catalog()["effects"]:
        merged[f"video_effect_{entry['name']}"] = {
            "category": "effects",
            "description": entry["description"],
            "params": entry["params"],
        }
    for entry in audio_effects.audio_effect_catalog()["effects"]:
        merged[f"audio_effect_{entry['name']}"] = {
            "category": "audio",
            "description": entry["description"],
            "params": entry["params"],
        }
    return merged


def catalog() -> dict[str, Any]:
    """Every video/audio operation grouped by category, with descriptions."""
    return grouped_catalog(_merge_effect_docs(), CATEGORY_ORDER)


def describe_operation(name: str) -> dict[str, Any]:
    """Explain one operation in plain language."""
    name = name.lower()
    docs = _merge_effect_docs()
    if name not in docs:
        raise ValueError(f"Unknown operation '{name}'.")
    return detail(name, docs[name])


def describe_timeline(project: VideoProject) -> dict[str, Any]:
    """Summarise a timeline in natural language for a non-vision reader."""
    scenes = project.scenes
    total = round(sum(scene.duration_seconds for scene in scenes), 1)
    words = sum(len((scene.narration or scene.text or "").split()) for scene in scenes)
    graded = sum(1 for scene in scenes if scene.grade.value != "none")
    filtered = sum(1 for scene in scenes if scene.filter.value != "none")
    effected = sum(1 for scene in scenes if scene.effect.value != "none")
    with_image = sum(1 for scene in scenes if scene.image_url or scene.video_url)
    summary = (
        f"This timeline has {len(scenes)} scenes running about {total}s "
        f"({project.aspect_ratio}, {project.fps}fps). It carries about {words} "
        f"words of narration. {with_image} of {len(scenes)} scenes have a source "
        f"image or video; {graded} have a colour grade, {filtered} a filter, and "
        f"{effected} an effect overlay."
    )
    return {
        "summary": summary,
        "details": {
            "scene_count": len(scenes),
            "total_seconds": total,
            "aspect_ratio": project.aspect_ratio,
            "fps": project.fps,
            "words": words,
            "scenes_with_image": with_image,
            "scenes_graded": graded,
            "scenes_filtered": filtered,
            "scenes_effected": effected,
            "marker_count": len(project.markers),
        },
    }


def suggest_edits(project: VideoProject) -> dict[str, Any]:
    """Turn the validator's findings into concrete, actionable edit steps."""
    from . import timeline

    issues = timeline.validate(project)
    suggestions: list[dict[str, Any]] = []
    for issue in issues:
        if issue.code == "scene_too_short":
            suggestions.append(
                {
                    "op": "set_scene_speed",
                    "params": {"scene_id": issue.scene_id, "speed": 1.0},
                    "reason": issue.message,
                }
            )
        elif issue.code == "low_text_contrast":
            suggestions.append(
                {
                    "op": "set_scene_text",
                    "params": {"scene_id": issue.scene_id, "text_style": "outline"},
                    "reason": issue.message,
                }
            )
        elif issue.code == "flat_look":
            suggestions.append(
                {
                    "op": "ai_assist",
                    "params": {"fit": False, "beat": False},
                    "reason": issue.message,
                }
            )
        elif issue.code == "narration_underfills":
            suggestions.append(
                {
                    "op": "ai_assist",
                    "params": {"fit": True, "beat": False},
                    "reason": issue.message,
                }
            )
        elif issue.code == "transition_too_long":
            suggestions.append(
                {
                    "op": "set_scene_transition",
                    "params": {"scene_id": issue.scene_id, "transition": "cut"},
                    "reason": issue.message,
                }
            )
        elif issue.code == "frantic_pacing":
            suggestions.append(
                {
                    "op": "merge_scene",
                    "params": {"scene_id": project.scenes[0].id},
                    "reason": issue.message,
                }
            )
    return {
        "suggestions": suggestions,
        "count": len(suggestions),
        "summary": (
            "No changes suggested — the timeline looks well-formed."
            if not suggestions
            else "Suggested edits based on the timeline report."
        ),
    }
