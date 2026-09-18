"""Narration script planning, linting and style models."""

from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, Field

from .common import (
    IssueSeverity,
    utcnow,
)


class ScriptSectionInfo(BaseModel):
    """One labelled section of a narration script, with timing estimates."""

    index: int
    label: str
    text: str
    unit_count: int
    estimated_seconds: float
    share: float


class ScriptDocument(BaseModel):
    """The structured view of a project's script that editors bind to.

    ``Project.script`` stays the raw text, because that is what the renderer
    narrates, what the linter analyses, and what every existing caller treats as a
    string. An editor wants the bundle *around* that text — the topic it serves,
    the style it was written in, its parsed sections and the timing plan — so the
    bundle is its own field rather than overloading ``script`` into a union, which
    would break every current consumer at once.
    """

    topic: str = ""
    style: str = ""
    raw_script: str = ""
    sections: list[ScriptSectionInfo] = Field(default_factory=list)
    timing_plan: ScriptPlan | None = None
    language: str = "vi"
    target_seconds: int = 0
    estimated_seconds: float = 0.0


class ScriptPlan(BaseModel):
    """Timing plan derived from a script and a target duration."""

    language: str
    target_seconds: int
    estimated_seconds: float
    fits_target: bool
    speech_units_per_second: float
    sections: list[ScriptSectionInfo] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utcnow)


# Historical alias: the severity scale is shared with the timeline validator.
ScriptIssueSeverity = IssueSeverity


class ScriptIssue(BaseModel):
    """A single finding from the script linter."""

    code: str
    severity: IssueSeverity
    message: str
    hint: str | None = None


class ScriptAnalysis(BaseModel):
    """The full analysis of a script: timing plan plus quality findings."""

    plan: ScriptPlan
    issues: list[ScriptIssue] = Field(default_factory=list)
    score: int = Field(default=100, ge=0, le=100)


class ScriptStyle(BaseModel):
    """A user-tunable scripting preset that drives the whole script stage.

    Built-in presets ship with the package; users can override them or add new
    ones by dropping JSON/Markdown files into the presets directory. Every
    field is consumed by :mod:`content_factory.script_engine` when it builds
    the prompt and lints the result, so the pipeline stays fully tunable.
    """

    name: str = Field(min_length=1, max_length=64)
    title: str = ""
    description: str = ""
    tone: str = "clear, conversational, confident"
    structure: list[str] = Field(
        default_factory=lambda: ["Hook", "Context", "Turn", "Payoff", "CTA"]
    )
    hook_rules: list[str] = Field(default_factory=list)
    sentence_max_units: int = Field(default=16, ge=4, le=60)
    units_per_second: dict[str, float] = Field(default_factory=dict)
    cta: str = ""
    banned_phrases: list[str] = Field(default_factory=list)
    language_notes: dict[str, str] = Field(default_factory=dict)
    max_sections: int = Field(default=14, ge=2, le=40)
    builtin: bool = True

    @property
    def slug(self) -> str:
        """Filesystem-safe identifier for this preset."""
        return re.sub(r"[^a-z0-9-]+", "-", self.name.lower()).strip("-") or "style"


class ScriptStyleSelect(BaseModel):
    """Payload for selecting the scripting preset of a project."""

    style: str = Field(min_length=1, max_length=64)


class ScriptAnalyzeRequest(BaseModel):
    """Payload for analysing a script without persisting it."""

    script: str | None = None
    style: str | None = None
