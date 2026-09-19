"""Turn a narration script into an editable, scene-based video project."""

from __future__ import annotations

import uuid

from .models import (
    ColorGrade,
    EntranceEffect,
    ExitEffect,
    KenBurns,
    OverlayPosition,
    SceneEffect,
    TextPosition,
    TextStyle,
    VideoFilter,
    VideoProject,
    VideoScene,
    VideoTransition,
)
from .script_engine import parse_script

# A rotating palette of cinematic backgrounds for auto-assigned scenes.
_BACKGROUNDS = (
    "#0f1117",
    "#1e1b4b",
    "#052e16",
    "#7c2d12",
    "#1e3a8a",
    "#831843",
    "#134e4a",
    "#3f3f46",
)


def _split_sections(script: str) -> list[tuple[str, str]]:
    """Split a script into ``(label, text)`` sections.

    Delegates to :func:`content_factory.script_engine.parse_script` so the
    scene builder, the timing planner, and the linter always agree on what a
    section is.
    """
    sections = parse_script(script)
    if not sections:
        return [("Scene 1", "")]
    return [(section.label, section.text) for section in sections]


def _distribute_durations(items: list[str], total_seconds: float) -> list[float]:
    """Assign proportional durations weighted by text length, capped at 60s."""
    weights = [max(1, len(text)) for text in items]
    total_weight = sum(weights)
    durations = [
        min(60.0, max(1.5, round(total_seconds * weight / total_weight, 1)))
        for weight in weights
    ]
    # Snap the last scene so the total matches the target (within the cap).
    remainder = total_seconds - sum(durations[:-1])
    durations[-1] = round(min(60.0, max(1.5, remainder)), 1)
    return durations


def build_video_project(
    script: str | None,
    total_seconds: int,
    language: str,
    previous: VideoProject | None = None,
) -> VideoProject:
    """Parse a script into a default, fully editable video project.

    When ``previous`` is given, scenes are matched to it by position and keep
    their ids. The pipeline rebuilds the timeline whenever it advances and
    ``build_video_project`` (the tool) rebuilds it on demand, so a fresh random
    id per build meant that an id an agent or the UI had just been handed
    turned into a 404 on the next call — through no fault of the caller. A
    scene keeps its identity across a rebuild; genuinely new scenes get new
    ids.
    """
    sections = _split_sections(script or "")
    texts = [text for _, text in sections]
    durations = _distribute_durations(texts, float(total_seconds))
    reused = list(previous.scenes) if previous is not None else []

    scenes: list[VideoScene] = []
    for index, ((label, text), duration) in enumerate(
        zip(sections, durations, strict=True)
    ):
        scenes.append(
            VideoScene(
                id=_stable_scene_id(reused, index),
                label=label,
                text=text or f"Scene {index + 1}",
                narration=text,
                duration_seconds=duration,
                speed=1.0,
                background=_BACKGROUNDS[index % len(_BACKGROUNDS)],
                transition=VideoTransition.FADE if index > 0 else VideoTransition.CUT,
                text_position=TextPosition.CENTER,
                text_color="#ffffff",
                font_size=44,
                text_style=TextStyle.NORMAL,
                filter=VideoFilter.NONE,
                ken_burns=KenBurns.NONE,
                entrance=EntranceEffect.FADE,
                exit=ExitEffect.NONE,
                motion=None,
                effect=SceneEffect.NONE,
                grade=ColorGrade.NONE,
                overlay_emoji=None,
                overlay_pos=OverlayPosition.TOP_RIGHT,
                overlay_size=48,
                pitch=1.0,
            )
        )
    return VideoProject(scenes=scenes, aspect_ratio="9:16", fps=30, captions=True)


def _stable_scene_id(previous: list[VideoScene], index: int) -> str:
    """The id this position already had, or a fresh one."""
    if index < len(previous):
        existing = previous[index].id
        if existing:
            return existing
    return uuid.uuid4().hex[:8]
