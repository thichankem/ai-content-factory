"""Tests for the conversational timeline assistant (natural-language editing)."""

from __future__ import annotations

from content_factory.models import VideoProject, VideoScene
from content_factory.nl_timeline import (
    TimelineIntent,
    apply_command,
    parse_command,
    resolve_scene_index,
)


def _project() -> VideoProject:
    scenes = [
        VideoScene(
            id="s1",
            label="Intro",
            text="You won't believe what happens next.",
            narration="You won't believe what happens next.",
            duration_seconds=4.0,
        ),
        VideoScene(
            id="s2",
            label="Body",
            text="The evidence is overwhelming.",
            narration="The evidence is overwhelming.",
            duration_seconds=6.0,
        ),
        VideoScene(
            id="s3",
            label="Outro",
            text="Follow for more.",
            narration="Follow for more.",
            duration_seconds=3.0,
        ),
    ]
    return VideoProject(scenes=scenes)


def test_parse_speed_up_intro() -> None:
    command = parse_command("speed up the intro to 1.5x")
    assert command.intent == TimelineIntent.SPEED_UP
    assert command.params["speed"] == 1.5
    assert command.target == "intro"


def test_parse_slow_down() -> None:
    command = parse_command("slow down the outro to 0.5x")
    assert command.intent == TimelineIntent.SLOW_DOWN
    assert command.params["speed"] == 0.5


def test_parse_delete_scene_number() -> None:
    command = parse_command("delete scene 3")
    assert command.intent == TimelineIntent.DELETE_SCENE
    assert resolve_scene_index(_project(), command.target) == 2


def test_parse_vietnamese_delete() -> None:
    command = parse_command("xoá cảnh 2")
    assert command.intent == TimelineIntent.DELETE_SCENE
    assert resolve_scene_index(_project(), command.target) == 1


def test_parse_add_marker_minutes() -> None:
    command = parse_command("add a marker at 2 minutes")
    assert command.intent == TimelineIntent.ADD_MARKER
    assert command.params["time"] == 120.0


def test_parse_merge_and_trim() -> None:
    assert (
        parse_command("merge the hook into the next scene").intent
        == TimelineIntent.MERGE_SCENE
    )
    assert parse_command("trim dead air").intent == TimelineIntent.TRIM


def test_apply_speed_up_changes_scene() -> None:
    project = _project()
    updated, command = apply_command(project, "speed up the intro to 1.5x")
    assert command.intent == TimelineIntent.SPEED_UP
    assert updated.scenes[0].speed == 1.5


def test_apply_delete_removes_scene() -> None:
    updated, _ = apply_command(_project(), "delete scene 2")
    assert len(updated.scenes) == 2
    assert updated.scenes[0].id == "s1"
    assert updated.scenes[1].id == "s3"


def test_apply_add_marker() -> None:
    updated, _ = apply_command(_project(), "add a marker at 5 seconds")
    assert len(updated.markers) == 1
    assert updated.markers[0].time_seconds == 5.0


def test_apply_unknown_leaves_project_unchanged() -> None:
    project = _project()
    updated, command = apply_command(project, "please make it more magical")
    assert command.intent == TimelineIntent.UNKNOWN
    assert updated is project


def test_apply_unresolved_scene_reports_failure() -> None:
    updated, command = apply_command(_project(), "speed up the nonexistent scene to 2x")
    assert command.intent == TimelineIntent.SPEED_UP
    assert "could not identify" in command.description
    assert len(updated.scenes) == 3
