"""External AI-agent catalog, briefs, results and tool-call payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .common import TwinSpelling, utcnow


class AgentInfo(BaseModel):
    """A configured AI agent/provider visible to the operator.

    Two audiences read this one record. The pipeline and the CLI describe a
    vendor with ``kind``/``tier``/``breaker``; the studio UIs render a card per
    agent and ask for ``id``/``role``/``provider``/``capabilities``. Rather than
    make each client translate, both sets of names are carried here and always
    describe the same vendor.
    """

    name: str
    kind: str
    tier: str
    enabled: bool
    model: str | None = None
    base_url: str | None = None
    breaker: str = "closed"
    #: Stable identifier for a UI: the vendor name, slugged.
    id: str = ""
    #: What the vendor is *for*, in the studio's vocabulary (``script``, ...).
    role: str = ""
    #: The vendor family, i.e. the configured ``kind``.
    provider: str = ""
    #: Work this agent can be routed, e.g. ``["script", "research"]``.
    capabilities: list[str] = Field(default_factory=list)


class CatalogStyle(BaseModel):
    """A scripting preset, in the shape a picker needs."""

    id: str
    name: str
    description: str = ""
    tone: str = ""


class CatalogVoice(BaseModel):
    """A neural narration voice the operator can select."""

    id: str
    name: str
    language: str
    gender: str = "female"
    engine: str = ""
    active: bool = False


class AgentCatalog(BaseModel):
    """Every AI agent the pipeline can route work to."""

    strategy: str
    tts_engine: str
    agents: list[AgentInfo] = Field(default_factory=list)
    preset_styles: list[str] = Field(default_factory=list)
    #: ``preset_styles`` as records, for clients that render a picker.
    script_styles: list[CatalogStyle] = Field(default_factory=list)
    #: Narration voices, with the configured override flagged ``active``.
    tts_voices: list[CatalogVoice] = Field(default_factory=list)


class AgentResultCreate(TwinSpelling):
    """Payload carrying a result produced by an external AI agent.

    ``markdown`` is the canonical field the CLI, the MCP server and the agent
    tools post; ``markdown_response`` is the spelling the studio UI sends.
    """

    PRIMARY = "markdown"
    ALIAS = "markdown_response"

    markdown: str | None = None
    markdown_response: str | None = None
    agent: str = "external-agent"

    @property
    def body(self) -> str:
        """The agent's reply, whichever field carried it."""
        return self.resolved


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
