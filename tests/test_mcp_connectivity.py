"""MCP connectivity tests for the AI Content Factory.

Verifies that the MCP server exposes the pipeline tools — including the new
NotebookLM-style ``kb_ask`` / ``kb_ingest_url`` — and that the tool dispatch
path the MCP server uses (``factory_call_tool`` → ``dispatch_tool``) actually
round-trips a knowledge call.

A separate live stdio handshake is exercised by ``scripts/test_mcp_live.py``
so the pytest suite stays fast and hermetic.
"""

from __future__ import annotations

import pytest

from content_factory import agent_tools
from content_factory.models import KBCreate, KBIngestText
from content_factory.providers import ProviderChain, ProviderTier, ScriptProvider


class _FakeProvider(ScriptProvider):
    def __init__(self, answer: str) -> None:
        self.name = "fake"
        self.model = "fake"
        self._answer = answer

    async def generate_script(self, prompt: str) -> str:
        return self._answer


def test_mcp_server_registers_factory_tools() -> None:
    import asyncio

    import mcp_server

    tools = asyncio.run(mcp_server.mcp.list_tools())
    names = {tool.name for tool in tools}
    assert "factory_list_tools" in names
    assert "factory_call_tool" in names
    assert "media_list" in names
    assert "voice_synthesize_speech" in names


def test_mcp_manifest_includes_knowledge_tools() -> None:
    manifest = agent_tools.build_tool_manifest()
    names = {tool["name"] for tool in manifest["tools"]}
    assert "kb_ask" in names
    assert "kb_ingest_url" in names


def test_mcp_dispatch_kb_ask_offline(service, settings) -> None:
    """The MCP dispatch path answers a KB question even with no provider."""
    kb = service.create_kb(KBCreate(name="Src", template="naive"))
    service.ingest_text(
        kb.id,
        KBIngestText(title="Doc", text="Morning light shapes city planning."),
    )
    result = agent_tools.dispatch_tool(
        service,
        "kb_ask",
        {"kb_id": kb.id, "query": "How does morning light affect cities?"},
    )
    assert result["grounded"] is False
    assert result["citations"]
    assert result["answer"]


def test_mcp_dispatch_kb_ask_grounded(service, settings) -> None:
    """The MCP dispatch path returns a synthesized answer when a provider exists."""
    service._providers = ProviderChain(
        settings,
        providers={
            ProviderTier.STRONG: _FakeProvider("Low sun casts long shadows. [1]")
        },
    )
    kb = service.create_kb(KBCreate(name="Src", template="naive"))
    service.ingest_text(
        kb.id,
        KBIngestText(title="Doc", text="Morning light shapes city planning."),
    )
    result = agent_tools.dispatch_tool(
        service,
        "kb_ask",
        {"kb_id": kb.id, "query": "How does morning light affect cities?"},
    )
    assert result["grounded"] is True
    assert result["provider"] == "fake"
    assert result["citations"]


def test_mcp_dispatch_kb_ask_requires_query(service) -> None:
    with pytest.raises(agent_tools.ToolError):
        agent_tools.dispatch_tool(service, "kb_ask", {"kb_id": "abc"})
