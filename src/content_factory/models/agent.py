"""External AI-agent catalog, briefs, results and tool-call payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .common import utcnow


class AgentInfo(BaseModel):
    """A configured AI agent/provider visible to the operator."""

    name: str
    kind: str
    tier: str
    enabled: bool
    model: str | None = None
    base_url: str | None = None
    breaker: str = "closed"


class AgentCatalog(BaseModel):
    """Every AI agent the pipeline can route work to."""

    strategy: str
    tts_engine: str
    agents: list[AgentInfo] = Field(default_factory=list)
    preset_styles: list[str] = Field(default_factory=list)


class AgentResultCreate(BaseModel):
    """Payload carrying a result produced by an external AI agent."""

    markdown: str = Field(min_length=1)
    agent: str = "external-agent"


class AgentBrief(BaseModel):
    """Metadata about the brief handed to an external AI agent."""

    project_id: str
    agent: str | None = None
    style: str
    markdown: str
    generated_at: datetime = Field(default_factory=utcnow)


class ToolCallRequest(BaseModel):
    """Payload for POST /tools/call (the agent tool dispatcher)."""

    tool: str = Field(min_length=1, max_length=60)
    args: dict[str, Any] = Field(default_factory=dict)
