"""Live MCP connectivity check for the AI Content Factory.

Spawns the real ``mcp_server.py`` over the stdio transport, connects with a
genuine MCP client, and proves the handshake plus a round-trip tool call — the
same path any MCP-capable agent (Claude, Codex, Gemini, ...) uses. Also asserts
the new NotebookLM-style knowledge tools are registered.

Run::

    python scripts/test_mcp_live.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

ROOT = Path(__file__).resolve().parent.parent
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"


def _text(content) -> str:
    """Join an MCP tool result's text content blocks."""
    parts = []
    for block in content:
        text = getattr(block, "text", None)
        if text is not None:
            parts.append(text)
    return "\n".join(parts)


async def main() -> int:
    params = StdioServerParameters(
        command=str(PYTHON), args=["mcp_server.py"], cwd=str(ROOT)
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            info = session.server_info
            print(f"[ok] connected to MCP server: {info.name} {info.version}")

            tools = await session.list_tools()
            names = {t.name for t in tools.tools}
            assert "factory_call_tool" in names, "factory_call_tool not registered"
            assert "factory_list_tools" in names, "factory_list_tools not registered"
            print(f"[ok] {len(names)} MCP tools registered (factory_call_tool present)")

            manifest_res = await session.call_tool("factory_list_tools", {})
            manifest = _text(manifest_res.content)
            for tool in ("kb_ask", "kb_ingest_url"):
                assert f'"{tool}"' in manifest, f"{tool} missing from manifest"
            print("[ok] knowledge tools kb_ask / kb_ingest_url in manifest")

            list_res = await session.call_tool(
                "factory_call_tool", {"tool_name": "list_kbs", "args_json": "{}"}
            )
            out = _text(list_res.content)
            print(f"[ok] factory_call_tool(list_kbs) -> {out.strip() or '(empty)'}")

    print("MCP LIVE CONNECTIVITY OK")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except Exception as exc:  # noqa: BLE001 - report the connectivity failure clearly
        print(f"MCP LIVE CONNECTIVITY FAILED: {exc}")
        sys.exit(1)
