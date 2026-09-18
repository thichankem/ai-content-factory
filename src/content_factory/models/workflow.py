"""Node/edge workflow definition and run bookkeeping."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .common import (
    IssueSeverity,
    utcnow,
)


class WorkflowNodeType(enum.StrEnum):
    """The kinds of block a production flow can contain."""

    RESEARCH = "research"
    SCRIPT = "script"
    LINT = "lint"
    GATE = "gate"
    VOICEOVER = "voiceover"
    SCENES = "scenes"
    AI_ASSIST = "ai_assist"
    TIMELINE_CHECK = "timeline_check"
    RENDER_PLAN = "render_plan"
    PUBLISH = "publish"
    INGEST_EXTERNAL = "ingest_external"


class WorkflowNode(BaseModel):
    """One draggable block in the flow canvas."""

    id: str
    type: WorkflowNodeType
    label: str = ""
    x: float = 0.0
    y: float = 0.0
    enabled: bool = True
    params: dict[str, Any] = Field(default_factory=dict)


class WorkflowEdge(BaseModel):
    """A link between two blocks: the target consumes the source's output."""

    id: str
    source: str
    target: str


class Workflow(BaseModel):
    """A drag-and-drop production flow attached to one project."""

    name: str = "Production pipeline"
    nodes: list[WorkflowNode] = Field(default_factory=list)
    edges: list[WorkflowEdge] = Field(default_factory=list)
    version: int = Field(default=1, ge=1)
    updated_at: datetime = Field(default_factory=utcnow)


class WorkflowCheckIssue(BaseModel):
    """One line of the pre-save checklist."""

    code: str
    severity: IssueSeverity
    message: str
    hint: str | None = None
    node_id: str | None = None


class WorkflowChecklist(BaseModel):
    """The pre-save checklist plus the resolved execution order."""

    issues: list[WorkflowCheckIssue] = Field(default_factory=list)
    ready: bool = True
    node_count: int = 0
    edge_count: int = 0
    order: list[str] = Field(default_factory=list)


class WorkflowSave(BaseModel):
    """Payload for saving a flow; ``force`` skips a failing checklist."""

    workflow: Workflow
    force: bool = False


class WorkflowRunStatus(enum.StrEnum):
    """Outcome of a flow run."""

    RUNNING = "running"
    OK = "ok"
    FAILED = "failed"
    BLOCKED = "blocked"


class WorkflowStepStatus(enum.StrEnum):
    """Outcome of a single block inside a run."""

    PENDING = "pending"
    RUNNING = "running"
    OK = "ok"
    SKIPPED = "skipped"
    FAILED = "failed"
    BLOCKED = "blocked"


class WorkflowStepResult(BaseModel):
    """What one block did, for the monitoring panel."""

    node_id: str
    label: str
    type: WorkflowNodeType
    status: WorkflowStepStatus = WorkflowStepStatus.PENDING
    duration_ms: int = 0
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class WorkflowRun(BaseModel):
    """A full run record: input variables, per-block detail, and timing."""

    id: str
    project_id: str
    status: WorkflowRunStatus = WorkflowRunStatus.RUNNING
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)
    steps: list[WorkflowStepResult] = Field(default_factory=list)
    message: str | None = None
    started_at: datetime = Field(default_factory=utcnow)
    finished_at: datetime | None = None
    duration_ms: int = 0


class WorkflowRunRequest(BaseModel):
    """Payload for running a flow (``inputs`` are the input variables)."""

    inputs: dict[str, Any] = Field(default_factory=dict)
