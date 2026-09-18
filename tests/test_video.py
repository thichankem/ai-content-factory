"""Tests for scene parsing and the video project endpoints."""

from __future__ import annotations

import pytest

from content_factory.models import (
    ApprovalCreate,
    EntranceEffect,
    ExitEffect,
    KenBurns,
    ProjectCreate,
    ScriptUpdate,
    TextStyle,
    VideoFilter,
    VideoProject,
    VideoScene,
    VideoTransition,
)
from content_factory.scenes import build_video_project
from content_factory.service import ContentFactoryService, StateConflictError

SCRIPT = (
    "[Hook]\nHave you noticed how morning light shapes your day?\n\n"
    "[Context]\nMost people walk past it.\n\n"
    "[Payoff]\nThat is the quiet power hiding in plain sight."
)


def test_build_video_project_parses_sections() -> None:
    project = build_video_project(SCRIPT, 45, "vi")
    assert [s.label for s in project.scenes] == ["Hook", "Context", "Payoff"]
    assert project.aspect_ratio == "9:16"
    assert project.fps == 30
    assert project.captions is True


def test_build_video_project_distributes_durations() -> None:
    project = build_video_project(SCRIPT, 45, "vi")
    total = sum(s.duration_seconds for s in project.scenes)
    assert abs(total - 45) <= 1.0
    assert all(s.duration_seconds >= 1.5 for s in project.scenes)


def test_build_video_project_defaults_new_fields() -> None:
    project = build_video_project(SCRIPT, 45, "vi")
    for scene in project.scenes:
        assert scene.speed == 1.0
        assert scene.filter == VideoFilter.NONE
        assert scene.ken_burns == KenBurns.NONE
        assert scene.text_style == TextStyle.NORMAL
        assert scene.entrance == EntranceEffect.FADE
        assert scene.exit == ExitEffect.NONE
        assert scene.transition in (VideoTransition.CUT, VideoTransition.FADE)


def test_build_video_project_freeform_script() -> None:
    project = build_video_project("Just a single paragraph of narration.", 30, "vi")
    assert len(project.scenes) >= 1
    assert project.scenes[0].text


def test_build_video_project_empty_script() -> None:
    project = build_video_project(None, 30, "vi")
    assert len(project.scenes) == 1
    assert project.scenes[0].label == "Scene 1"


def test_update_video_project_persists_edits(service: ContentFactoryService) -> None:
    project = service.create_project(
        ProjectCreate(name="V", topic="topic", duration_target_seconds=30)
    )
    service.update_script(
        project.id, ScriptUpdate(script=SCRIPT, source_rights_confirmed=True)
    )
    service.approve(project.id, ApprovalCreate(stage="script", verdict="approved"))
    service.start_generation(project.id)
    service.complete_generation(project.id)
    assert project.video_project is not None

    edit = VideoProject(
        scenes=[
            VideoScene(id="s1", label="Custom", text="Edited text", duration_seconds=5)
        ],
        aspect_ratio="16:9",
        fps=60,
        export_quality="low",
    )
    updated = service.update_video_project(project.id, edit)
    assert updated.video_project is not None
    assert updated.video_project.aspect_ratio == "16:9"
    assert updated.video_project.fps == 60
    assert updated.video_project.scenes[0].text == "Edited text"


def test_upload_video_sets_asset(service: ContentFactoryService) -> None:
    project = service.create_project(
        ProjectCreate(name="V", topic="topic", duration_target_seconds=30)
    )
    service.update_script(
        project.id, ScriptUpdate(script=SCRIPT, source_rights_confirmed=True)
    )
    service.approve(project.id, ApprovalCreate(stage="script", verdict="approved"))
    service.start_generation(project.id)
    service.complete_generation(project.id)

    uploaded = service.upload_video(
        project.id, "video.webm", b"\x1a\x45\xdf\xa3 fake webm"
    )
    assert uploaded.video is not None
    assert uploaded.video.format == "webm"
    assert uploaded.video.size_bytes == 14
    assert service.video_path(project.id) is not None


def test_upload_video_blocked_in_draft(service: ContentFactoryService) -> None:
    project = service.create_project(
        ProjectCreate(name="V", topic="topic", duration_target_seconds=30)
    )
    with pytest.raises(StateConflictError):
        service.upload_video(project.id, "v.webm", b"data")


def test_benchmark_script_runs() -> None:
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "scripts/benchmark.py", "--runs", "1"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    assert "build_video_project" in result.stdout
    assert "library.search" in result.stdout
