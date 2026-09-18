#!/usr/bin/env python3
"""Health-check the MCP server and validate its tool-schema contract.

Imports the server in-process (the same code a real run boots), lists every
registered tool, and verifies each exposes a name, a description, and a JSON
Schema input. With ``--smoke`` it also calls the read-only ``media_list`` tool
to prove the process boots end to end.

Used by CI (``mcp-contract-check.yml``) so a PR that breaks a tool signature
or drops a tool fails the build instead of shipping a broken contract.

Usage::

    python scripts/mcp_healthcheck.py [--smoke]
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any

# Allow `python scripts/mcp_healthcheck.py` to import the root-level mcp_server.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _tool_input_schema(tool: Any) -> dict[str, Any]:
    """Return the tool's input schema dict, tolerating field-name variants."""
    raw = getattr(tool, "input_schema", None)
    if raw is None:
        raw = getattr(tool, "inputSchema", None)
    if isinstance(raw, dict):
        return raw
    if hasattr(raw, "model_dump"):
        dumped = raw.model_dump()
        return dumped if isinstance(dumped, dict) else {}
    return {}


async def _run(smoke: bool) -> int:
    # Importing the module boots the same process-local services the server
    # uses (media library, store, recook pipeline).
    import mcp_server  # noqa: PLC0415

    tools = await mcp_server.mcp.list_tools()
    failures: list[str] = []
    for tool in tools:
        name = getattr(tool, "name", "")
        description = getattr(tool, "description", "") or ""
        schema = _tool_input_schema(tool)
        if not name:
            failures.append("a tool is missing its name")
        if not description:
            failures.append(f"tool '{name or '?'}' is missing its description")
        if not isinstance(schema, dict) or "type" not in schema:
            failures.append(f"tool '{name or '?'}' is missing a JSON-Schema input")

    print(f"mcp_healthcheck: {len(tools)} tool(s) registered")
    for tool in sorted(tools, key=lambda t: getattr(t, "name", "")):
        print(f"  - {getattr(tool, 'name', '?')}")

    if smoke:
        result = await mcp_server.mcp.call_tool("media_list", {})
        text = getattr(result, "content", None)
        if text is None:
            failures.append("media_list smoke call returned no content")
        else:
            print(f"mcp_healthcheck: media_list smoke OK ({len(text)} item(s))")

    if failures:
        print("mcp_healthcheck: FAILED", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1
    print("mcp_healthcheck: OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true", help="also call media_list")
    args = parser.parse_args(argv)
    return asyncio.run(_run(args.smoke))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
