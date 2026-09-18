"""Fusion node-graph models (DaVinci Resolve-style compositing).

Mirrors ``docs/NLE-STUDIO-FULL-ARCHITECTURE.md`` §3.5. The graph is validated
before it is executed — a cycle or a socket wired to a missing node is a
configuration error, and reporting it beats rendering a black frame.
"""

from __future__ import annotations

import enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class FusionNodeType(enum.StrEnum):
    """The kinds of node a compositing graph can contain."""

    INPUT = "input"
    AI_TRANSFORM = "ai"
    EFFECT = "effect"
    MERGE = "merge"
    OUTPUT = "output"


class FusionBlendOperator(enum.StrEnum):
    """How a merge node combines its two inputs."""

    OVER = "Over"
    SCREEN = "Screen"
    MULTIPLY = "Multiply"
    ADD = "Add"
    SUBTRACT = "Subtract"
    UNDER = "Under"


class FusionNodeSocket(BaseModel):
    """One input or output socket of a node."""

    name: str
    socket_type: Literal["image", "mask", "audio", "data"]
    connected_to: str | None = None


class FusionNode(BaseModel):
    """One node inside the compositing graph."""

    id: str
    name: str
    node_type: FusionNodeType
    pos_x: float
    pos_y: float
    params: dict[str, Any] = Field(default_factory=dict)
    inputs: list[FusionNodeSocket] = Field(default_factory=list)
    outputs: list[FusionNodeSocket] = Field(default_factory=list)
    is_cached: bool = False
    is_active: bool = True


class FusionGraphPayload(BaseModel):
    """A directed acyclic compositing graph for one project."""

    project_id: str
    nodes: list[FusionNode] = Field(default_factory=list)
    output_resolution: Literal[
        "1080x1920", "1920x1080", "2160x3840", "3840x2160"
    ] = "1080x1920"
    color_space: Literal["Rec.709", "DaVinci Wide Gamut", "sRGB"] = "Rec.709"
    bit_depth: Literal["8-bit", "10-bit", "16-bit float", "32-bit float"] = "10-bit"


class FusionValidationReport(BaseModel):
    """What the graph validator found, before anything is rendered."""

    ready: bool
    issues: list[str] = Field(default_factory=list)
    node_count: int = 0
    order: list[str] = Field(default_factory=list)


class FusionRenderResult(BaseModel):
    """The outcome of compiling and evaluating a graph."""

    task_id: str
    status: Literal["completed", "failed"]
    output_url: str | None = None
    nodes_executed: int = 0
    cache_hits: int = 0
    warnings: list[str] = Field(default_factory=list)
    duration_ms: int = 0