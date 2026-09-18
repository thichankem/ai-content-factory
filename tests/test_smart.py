"""Tests for the AI-assisted editing intelligence (smart.py)."""

from __future__ import annotations

import pytest

from content_factory.models import (
    ApprovalCreate,
    ColorGrade,
    ProjectCreate,
    SceneEffect,
    ScriptUpdate,
    VideoFilter,
    VideoProject,
    VideoScene,
    VideoTransition,
)
from content_factory.scenes import build_video_project
from content_factory.smart import (
    apply_ai_assist,
    auto_fit_durations,
    beat_sync,
    captions_from_narration,
    polish_text,
    suggest_all,
    suggest_effect,
    suggest_filter,
    suggest_grade,
    suggest_transition,
)

SCRIPT = """
# Hook
This video reveals the secret.

# Evidence
Night footage proves the digital crime.

# Payoff
Subscribe for more tech mysteries.
"""


def make_project() -> VideoProject:
    return build_video_project(SCRIPT, 30, "en")


def test_auto_fit_rebalances_by_text_length() -> None:
    project = make_project()
    before = [s.duration_seconds for s in project.scenes]
    auto_fit_durations(project, target_total=30.0)
    after = [s.duration_seconds for s in project.scenes]
    assert sum(after) == pytest.approx(30.0, abs=0.5)
    assert after != before


def test_beat_sync_snaps_to_grid() -> None:
    project = make_project()
    beat_sync(project, bpm=120)
    for scene in project.scenes:
        assert scene.duration_seconds == pytest.approx(
            round(scene.duration_seconds / 0.5) * 0.5
        )


def test_suggest_filter_from_keywords() -> None:
    scene = VideoScene(id="1", label="Evidence", text="night footage")
    assert suggest_filter(scene) == VideoFilter.COOL
    scene2 = VideoScene(id="2", label="Intro", text="sunrise gold morning")
    assert suggest_filter(scene2) == VideoFilter.WARM


def test_suggest_effect_from_keywords() -> None:
    scene = VideoScene(id="1", label="Tech", text="digital glitch hack")
    assert suggest_effect(scene) == SceneEffect.GLITCH
    scene2 = VideoScene(id="2", label="Memory", text="old film nostalgia")
    assert suggest_effect(scene2) == SceneEffect.SCANLINES


def test_suggest_grade_from_keywords() -> None:
    scene = VideoScene(id="1", label="Action", text="blockbuster cinematic epic")
    assert suggest_grade(scene) == ColorGrade.TEAL_ORANGE
    scene2 = VideoScene(id="2", label="Future", text="cyber neon tech")
    assert suggest_grade(scene2) == ColorGrade.CYBERPUNK


def test_suggest_transition_from_keywords() -> None:
    scene = VideoScene(id="1", label="Twist", text="suddenly reveal")
    assert suggest_transition(scene) == VideoTransition.ZOOM


def test_suggest_all_returns_strings() -> None:
    scene = VideoScene(id="1", label="Evidence", text="night crime mystery")
    suggestions = suggest_all(scene)
    assert set(suggestions) == {"filter", "effect", "grade", "transition"}
    assert suggestions["filter"] == "cool"
    assert suggestions["grade"] == "noir"


def test_polish_text_capitalizes_and_terminates() -> None:
    assert polish_text("hello world") == "Hello world."
    assert polish_text("  spaced   out  ") == "Spaced out."
    assert polish_text("Already good!") == "Already good!"


def test_captions_from_narration_chunks_long_text() -> None:
    scenes = [
        VideoScene(id="1", label="A", text="short"),
        VideoScene(
            id="2",
            label="B",
            text="one two three four five six seven eight nine ten eleven twelve",
        ),
    ]
    captions = captions_from_narration(scenes)
    assert captions[0] == "short"
    assert len(captions[1].split()) <= 8


def test_apply_ai_assist_full_pipeline() -> None:
    project = make_project()
    apply_ai_assist(project, fit=True, beat=True, bpm=100)
    assert len(project.scenes) == 3
    for scene in project.scenes:
        assert scene.text.endswith(".")
        assert scene.text[0].isupper()
    assert project.scenes[1].filter == VideoFilter.COOL
    assert project.scenes[1].grade == ColorGrade.NOIR
    assert project.scenes[1].effect == SceneEffect.GLITCH


def test_apply_ai_assist_leaves_first_transition_cut() -> None:
    project = make_project()
    apply_ai_assist(project, fit=False, beat=False, bpm=120)
    assert project.scenes[0].transition == VideoTransition.CUT


def test_new_scene_fields_defaults() -> None:
    project = make_project()
    scene = project.scenes[0]
    assert scene.motion is None
    assert scene.effect == SceneEffect.NONE
    assert scene.grade == ColorGrade.NONE
    assert scene.overlay_emoji is None
    assert scene.pitch == 1.0
    assert project.bpm == 120


def test_scene_motion_roundtrip() -> None:
    from content_factory.models import SceneMotion

    project = make_project()
    scene = project.scenes[0]
    scene.motion = SceneMotion(
        scale=1.4, rotation=12, opacity=0.8, pos_x=10, pos_y=-5, easing="ease-out"
    )
    restored = VideoProject.model_validate(project.model_dump())
    assert restored.scenes[0].motion is not None
    assert restored.scenes[0].motion.scale == 1.4
    assert restored.scenes[0].motion.easing == "ease-out"


def test_service_ai_assist_endpoint(service) -> None:
    project = service.create_project(
        ProjectCreate(name="V", topic="t", duration_target_seconds=30)
    )
    service.update_script(
        project.id, ScriptUpdate(script=SCRIPT, source_rights_confirmed=True)
    )
    service.approve(project.id, ApprovalCreate(stage="script", verdict="approved"))
    service.start_generation(project.id)
    service.complete_generation(project.id)

    updated = service.apply_ai_assist(project.id, fit=True, beat=True, bpm=120)
    assert updated.video_project is not None
    assert all(s.text.endswith(".") for s in updated.video_project.scenes)

    suggestions = service.ai_suggest_scene(
        project.id, updated.video_project.scenes[0].id
    )
    assert "filter" in suggestions

    polished = service.polish_scene_text(project.id, updated.video_project.scenes[0].id)
    assert polished.video_project is not None
