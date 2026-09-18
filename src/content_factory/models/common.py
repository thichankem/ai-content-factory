"""Shared value objects: timestamps, lifecycle enums, health payload."""

from __future__ import annotations

import enum
from datetime import UTC, datetime

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    """Timezone-aware UTC now, used as the default for timestamps."""
    return datetime.now(UTC)


class ProjectStatus(enum.StrEnum):
    """Lifecycle states of a project."""

    DRAFT = "draft"
    SCRIPT_REVIEW = "script_review"
    SCRIPT_APPROVED = "script_approved"
    GENERATING = "generating"
    VIDEO_REVIEW = "video_review"
    VIDEO_APPROVED = "video_approved"
    PUBLISHED = "published"
    FAILED = "failed"


class ApprovalStage(enum.StrEnum):
    """The two mandatory human review gates."""

    SCRIPT = "script"
    VIDEO = "video"


class ApprovalVerdict(enum.StrEnum):
    """Outcome of a human review gate."""

    APPROVED = "approved"
    REJECTED = "rejected"


class IssueSeverity(enum.StrEnum):
    """How serious a reported finding is.

    Shared by the script linter and the timeline validator so a client can
    render both with one rule set.
    """

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ApprovalRecord(BaseModel):
    """A single human review decision on a project."""

    stage: ApprovalStage
    verdict: ApprovalVerdict
    comment: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class HealthResponse(BaseModel):
    """Payload for ``GET /health``."""

    status: str
    app: str
    version: str
    providers: dict[str, str]
