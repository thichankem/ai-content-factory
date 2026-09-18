"""AI-assisted editing intelligence.

Pure functions that power the one-click AI editing actions in the video
editor: auto-fitting scene durations to narration, snapping scenes to a music
beat grid, suggesting filters/transitions from scene content, polishing scene
text, and deriving captions from narration.
"""

from __future__ import annotations

import re

from .models import (
    ColorGrade,
    SceneEffect,
    VideoFilter,
    VideoProject,
    VideoScene,
    VideoTransition,
)
from .text import tokenize

# Keyword → suggested filter for the "AI suggest" action.
_FILTER_HINTS: tuple[tuple[tuple[str, ...], VideoFilter], ...] = (
    (("night", "dark", "moon", "midnight", "space"), VideoFilter.COOL),
    (("sun", "sunrise", "morning", "gold", "warm", "fire"), VideoFilter.WARM),
    (("sad", "loss", "memory", "past", "old"), VideoFilter.SEPIA),
    (("tech", "ai", "code", "digital", "future"), VideoFilter.CONTRAST),
    (("dream", "love", "calm", "peace", "gentle"), VideoFilter.BRIGHTNESS),
    (("crime", "mystery", "serious", "noir"), VideoFilter.GRAYSCALE),
)

# Keyword → suggested effect.
_EFFECT_HINTS: tuple[tuple[tuple[str, ...], SceneEffect], ...] = (
    (("glitch", "error", "hack", "digital"), SceneEffect.GLITCH),
    (("retro", "vhs", "80s", "nostalgia"), SceneEffect.SCANLINES),
    (("film", "cinema", "movie", "hollywood"), SceneEffect.FILM_GRAIN),
    (("dream", "fantasy", "magic"), SceneEffect.DREAMY),
    (("old", "vintage", "history", "memory"), SceneEffect.OLD_FILM),
)

# Keyword → suggested color grade.
_GRADE_HINTS: tuple[tuple[tuple[str, ...], ColorGrade], ...] = (
    (("action", "blockbuster", "cinematic", "epic"), ColorGrade.TEAL_ORANGE),
    (("crime", "mystery", "serious", "drama"), ColorGrade.NOIR),
    (("retro", "vintage", "old", "memory"), ColorGrade.VINTAGE),
    (("tech", "future", "cyber", "neon"), ColorGrade.CYBERPUNK),
    (("love", "dream", "gentle", "calm"), ColorGrade.PASTEL),
)

# Keyword → suggested transition.
_TRANSITION_HINTS: tuple[tuple[tuple[str, ...], VideoTransition], ...] = (
    (("intro", "start", "begin", "hook"), VideoTransition.FADE),
    (("turn", "twist", "reveal", "suddenly"), VideoTransition.ZOOM),
    (("end", "outro", "conclusion", "payoff", "cta"), VideoTransition.FADE),
    (("evidence", "data", "list", "compare"), VideoTransition.WIPE),
)

_STOPWORDS = frozenset(
    {"the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with"}
)


def _keywords(text: str) -> set[str]:
    return set(tokenize(text, min_length=3, stopwords=_STOPWORDS))


def auto_fit_durations(
    project: VideoProject, target_total: float | None = None
) -> VideoProject:
    """Rebalance scene durations proportionally to text length."""
    if not project.scenes:
        return project
    total = target_total or sum(scene.duration_seconds for scene in project.scenes)
    weights = [max(1, len(scene.text or "")) for scene in project.scenes]
    weight_sum = sum(weights)
    for scene, weight in zip(project.scenes, weights, strict=True):
        scene.duration_seconds = round(max(1.5, total * weight / weight_sum), 1)
    return project


def beat_sync(project: VideoProject, bpm: int) -> VideoProject:
    """Snap every scene duration to a multiple of the beat length."""
    beat = 60.0 / max(60, min(180, int(bpm)))
    for scene in project.scenes:
        beats = max(1, round(scene.duration_seconds / beat))
        scene.duration_seconds = round(beats * beat, 2)
    return project


def suggest_filter(scene: VideoScene) -> VideoFilter:
    keywords = _keywords(f"{scene.label} {scene.text}")
    for hints, suggestion in _FILTER_HINTS:
        if keywords & set(hints):
            return suggestion
    return VideoFilter.NONE


def suggest_effect(scene: VideoScene) -> SceneEffect:
    keywords = _keywords(f"{scene.label} {scene.text}")
    for hints, suggestion in _EFFECT_HINTS:
        if keywords & set(hints):
            return suggestion
    return SceneEffect.NONE


def suggest_grade(scene: VideoScene) -> ColorGrade:
    keywords = _keywords(f"{scene.label} {scene.text}")
    for hints, suggestion in _GRADE_HINTS:
        if keywords & set(hints):
            return suggestion
    return ColorGrade.NONE


def suggest_transition(scene: VideoScene) -> VideoTransition:
    keywords = _keywords(f"{scene.label} {scene.text}")
    for hints, suggestion in _TRANSITION_HINTS:
        if keywords & set(hints):
            return suggestion
    return VideoTransition.FADE


def suggest_all(scene: VideoScene) -> dict[str, str]:
    """Return the AI suggestion set for a scene."""
    return {
        "filter": suggest_filter(scene).value,
        "effect": suggest_effect(scene).value,
        "grade": suggest_grade(scene).value,
        "transition": suggest_transition(scene).value,
    }


def polish_text(text: str) -> str:
    """Light AI-style rewrite: tighten, capitalize, and add punch."""
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    # Strip markdown heading / bullet markers left over from the script.
    cleaned = re.sub(r"^(#{1,6}|\*|\-|\d+\.)\s*", "", cleaned)
    if not cleaned:
        return cleaned
    cleaned = cleaned[0].upper() + cleaned[1:]
    if not cleaned.endswith((".", "!", "?", "…")):
        cleaned += "."
    if len(cleaned) > 3 and cleaned[-2] == ".":
        cleaned = cleaned[:-2] + cleaned[-1]
    return cleaned


def captions_from_narration(scenes: list[VideoScene]) -> list[str]:
    """Derive a caption string per scene from its narration/text."""
    captions: list[str] = []
    for scene in scenes:
        source = scene.narration or scene.text or ""
        words = source.split()
        if len(words) <= 8:
            captions.append(source.strip())
        else:
            # Keep captions short and punchy: first sentence or first 8 words.
            first_sentence = re.split(r"(?<=[.!?])\s+", source.strip())[0]
            if len(first_sentence.split()) <= 8:
                captions.append(first_sentence)
            else:
                captions.append(" ".join(words[:8]) + "…")
    return captions


def apply_ai_assist(
    project: VideoProject, *, fit: bool, beat: bool, bpm: int
) -> VideoProject:
    """Apply the AI auto-edit pipeline to a video project."""
    if fit:
        auto_fit_durations(project)
    if beat:
        beat_sync(project, bpm)
    for index, scene in enumerate(project.scenes):
        scene.filter = suggest_filter(scene)
        scene.effect = suggest_effect(scene)
        scene.grade = suggest_grade(scene)
        if index > 0:
            scene.transition = suggest_transition(scene)
        scene.text = polish_text(scene.text)
    return project
