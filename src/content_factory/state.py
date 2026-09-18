"""Project lifecycle state machine."""

from __future__ import annotations

from .models import ProjectStatus

# Allowed transitions between lifecycle states.
_TRANSITIONS: dict[ProjectStatus, frozenset[ProjectStatus]] = {
    ProjectStatus.DRAFT: frozenset({ProjectStatus.SCRIPT_REVIEW}),
    ProjectStatus.SCRIPT_REVIEW: frozenset({ProjectStatus.SCRIPT_APPROVED}),
    ProjectStatus.SCRIPT_APPROVED: frozenset({ProjectStatus.GENERATING}),
    ProjectStatus.GENERATING: frozenset(
        {ProjectStatus.VIDEO_REVIEW, ProjectStatus.FAILED}
    ),
    ProjectStatus.VIDEO_REVIEW: frozenset(
        {ProjectStatus.VIDEO_APPROVED, ProjectStatus.GENERATING}
    ),
    ProjectStatus.VIDEO_APPROVED: frozenset({ProjectStatus.PUBLISHED}),
    ProjectStatus.PUBLISHED: frozenset(),
    ProjectStatus.FAILED: frozenset({ProjectStatus.GENERATING}),
}


class StateMachineError(Exception):
    """Raised when a requested state transition is not allowed."""


def can_transition(current: ProjectStatus, target: ProjectStatus) -> bool:
    """Return whether ``current -> target`` is a legal transition."""
    return target in _TRANSITIONS[current]


def assert_transition(current: ProjectStatus, target: ProjectStatus) -> None:
    """Raise :class:`StateMachineError` if the transition is illegal."""
    if not can_transition(current, target):
        raise StateMachineError(
            f"Cannot transition from '{current.value}' to '{target.value}'."
        )
