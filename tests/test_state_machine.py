"""Tests for the project lifecycle state machine."""

from __future__ import annotations

import pytest

from content_factory.models import ProjectStatus
from content_factory.state import StateMachineError, assert_transition, can_transition


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (ProjectStatus.DRAFT, ProjectStatus.SCRIPT_REVIEW),
        (ProjectStatus.SCRIPT_REVIEW, ProjectStatus.SCRIPT_APPROVED),
        (ProjectStatus.SCRIPT_APPROVED, ProjectStatus.GENERATING),
        (ProjectStatus.GENERATING, ProjectStatus.VIDEO_REVIEW),
        (ProjectStatus.GENERATING, ProjectStatus.FAILED),
        (ProjectStatus.VIDEO_REVIEW, ProjectStatus.VIDEO_APPROVED),
        (ProjectStatus.VIDEO_REVIEW, ProjectStatus.GENERATING),
        (ProjectStatus.VIDEO_APPROVED, ProjectStatus.PUBLISHED),
        (ProjectStatus.FAILED, ProjectStatus.GENERATING),
    ],
)
def test_valid_transitions(current: ProjectStatus, target: ProjectStatus) -> None:
    assert can_transition(current, target)
    assert_transition(current, target)  # should not raise


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (ProjectStatus.DRAFT, ProjectStatus.SCRIPT_APPROVED),
        (ProjectStatus.DRAFT, ProjectStatus.GENERATING),
        (ProjectStatus.SCRIPT_REVIEW, ProjectStatus.GENERATING),
        (ProjectStatus.SCRIPT_APPROVED, ProjectStatus.DRAFT),
        (ProjectStatus.SCRIPT_APPROVED, ProjectStatus.PUBLISHED),
        (ProjectStatus.VIDEO_APPROVED, ProjectStatus.DRAFT),
        (ProjectStatus.PUBLISHED, ProjectStatus.DRAFT),
        (ProjectStatus.PUBLISHED, ProjectStatus.PUBLISHED),
        (ProjectStatus.FAILED, ProjectStatus.DRAFT),
        (ProjectStatus.FAILED, ProjectStatus.VIDEO_APPROVED),
    ],
)
def test_invalid_transitions_raise(
    current: ProjectStatus, target: ProjectStatus
) -> None:
    assert not can_transition(current, target)
    with pytest.raises(StateMachineError):
        assert_transition(current, target)


def test_published_is_terminal() -> None:
    assert can_transition(ProjectStatus.PUBLISHED, ProjectStatus.PUBLISHED) is False


def test_no_self_transition_by_default() -> None:
    assert can_transition(ProjectStatus.DRAFT, ProjectStatus.DRAFT) is False
