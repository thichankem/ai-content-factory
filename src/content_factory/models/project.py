"""Project aggregate and its lifecycle request payloads."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from .campaign import MultiFormatCampaign
from .common import (
    ApprovalRecord,
    ApprovalStage,
    ApprovalVerdict,
    ProjectStatus,
    utcnow,
)
from .external import ExternalAssetRecord
from .history import (
    FactReconciliationReport,
    SensitivityAuditReport,
    StructuredTimeline,
)
from .knowledge import GroundingBundle
from .research import (
    DocumentRef,
    ResearchBundle,
)
from .script import (
    ScriptDocument,
    ScriptIssue,
    ScriptPlan,
)
from .timeline import VideoProject
from .voice import VoiceoverBundle
from .workflow import Workflow


class ProjectCreate(BaseModel):
    """Payload for creating a project."""

    name: str = Field(min_length=1, max_length=120)
    topic: str = Field(min_length=1, max_length=500)
    target_language: str = "vi"
    duration_target_seconds: int = Field(default=45, ge=5, le=600)


class ScriptUpdate(BaseModel):
    """Payload for saving a script and confirming source rights.

    ``script`` is the canonical field; ``raw_script`` is the name both web clients
    send, because they think of it as the raw text behind the parsed sections.
    Exactly one of the two is required.
    """

    script: str | None = None
    raw_script: str | None = None
    source_rights_confirmed: bool = False

    @property
    def text(self) -> str:
        """The script body, whichever field carried it."""
        return self.script if self.script is not None else (self.raw_script or "")

    @model_validator(mode="after")
    def _require_a_script(self) -> ScriptUpdate:
        if not self.text.strip():
            raise ValueError("provide 'script' (or its alias 'raw_script')")
        return self


class ApprovalCreate(BaseModel):
    """Payload for submitting a human review decision."""

    stage: ApprovalStage
    verdict: ApprovalVerdict
    comment: str | None = None


class VideoAsset(BaseModel):
    """Metadata for a produced video."""

    asset_url: str
    thumbnail_url: str
    duration_seconds: int
    format: str = "mp4"
    size_bytes: int | None = None


class PublishCreate(BaseModel):
    """Payload for publishing an approved video."""

    platforms: list[str] = Field(default_factory=lambda: ["youtube"])


class Project(BaseModel):
    """A content production unit tracked through the pipeline."""

    id: str
    name: str
    topic: str
    target_language: str
    duration_target_seconds: int
    status: ProjectStatus = ProjectStatus.DRAFT
    script: str | None = None
    #: Structured view of ``script`` (sections, timing, style) for editors.
    #: ``script`` itself stays the raw text every other consumer expects.
    script_document: ScriptDocument | None = None
    source_rights_confirmed: bool = False
    approvals: list[ApprovalRecord] = Field(default_factory=list)
    provider_used: str | None = None
    error: str | None = None
    progress: int | None = None
    video: VideoAsset | None = None
    platforms: list[str] = Field(default_factory=list)
    published_at: datetime | None = None
    research: ResearchBundle | None = None
    documents: list[DocumentRef] = Field(default_factory=list)
    # RAGFlow-style knowledge base attached to this project.
    knowledge_base_id: str | None = None
    # Last grounding pass: retrieved chunks that grounded the current script.
    grounding: GroundingBundle | None = None
    video_project: VideoProject | None = None
    voiceover: VoiceoverBundle | None = None
    script_style: str = "viral-short"
    script_plan: ScriptPlan | None = None
    script_issues: list[ScriptIssue] = Field(default_factory=list)
    agent_used: str | None = None
    workflow: Workflow | None = None
    campaign: MultiFormatCampaign | None = None
    external_assets: list[ExternalAssetRecord] = Field(default_factory=list)
    structured_timeline: StructuredTimeline | None = None
    fact_report: FactReconciliationReport | None = None
    sensitivity_report: SensitivityAuditReport | None = None
    # Media-library item this project was re-cooked from (for source footage).
    source_media_id: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
