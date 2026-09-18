"""Shared value objects: timestamps, lifecycle enums, health payload."""

from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import ClassVar, Self

from pydantic import BaseModel, Field, model_validator


def utcnow() -> datetime:
    """Timezone-aware UTC now, used as the default for timestamps."""
    return datetime.now(UTC)


class TwinSpelling(BaseModel):
    """A required text value that two clients spell two different ways.

    The same drift kept appearing across the request models: the CLI, the
    pipeline and the agent tools name a field one way, the web clients name it
    another, and whichever spelling the model does not declare produces a 422 on
    a request that is semantically perfect. Worse, on a field with a default it
    produces something quieter than an error — a confident empty result.

    A subclass declares the two field names it accepts as :attr:`PRIMARY` and
    :attr:`ALIAS` and gets the whole rule for free: either spelling validates,
    both together validate (a non-empty primary wins), neither fails with a
    message that names both, and :attr:`resolved` returns the value stripped.
    Subclasses keep their own public accessors, so the vocabulary each caller
    already uses does not change.

    Only string-valued pairs belong here. A pair whose two spellings are
    genuinely different types is not a spelling difference and needs its own
    rule.
    """

    #: The canonical field name, as spelled by the pipeline and agent tools.
    PRIMARY: ClassVar[str] = ""
    #: The alternate field name, as spelled by the web clients.
    ALIAS: ClassVar[str] = ""

    @property
    def resolved(self) -> str:
        """The value, whichever field carried it, with surrounding space removed."""
        primary = getattr(self, self.PRIMARY, None) or ""
        alias = getattr(self, self.ALIAS, None) or ""
        return (primary or alias).strip()

    @model_validator(mode="after")
    def _require_a_spelling(self) -> Self:
        if not self.resolved:
            raise ValueError(f"provide '{self.PRIMARY}' (or its alias '{self.ALIAS}')")
        return self


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
