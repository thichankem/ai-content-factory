"""Self-describing agent tool registry endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from ... import agent_tools
from ...models import ToolCallRequest
from ...service import (
    ContentFactoryService,
    NotFoundError,
    RightsNotConfirmedError,
    StateConflictError,
)


def build_router(service: ContentFactoryService) -> APIRouter:

    router = APIRouter()

    @router.get("/tools")
    def tools_manifest(
        q: str | None = None,
        category: str | None = None,
        detail: str = "full",
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Machine-readable tool manifest so an agent can discover everything.

        Filter before you fetch: ``?q=duck+music`` finds the tool, ``?detail=index``
        answers with one line per tool, ``?limit=5`` caps the page.  The reply
        always carries ``total`` and ``has_more`` so a short answer is never
        mistaken for the whole catalog.
        """
        if detail not in {"full", "index"}:
            raise HTTPException(
                status_code=422, detail="detail must be 'full' or 'index'."
            )
        return agent_tools.build_tool_manifest(
            q=q, category=category, detail=detail, limit=limit
        )

    @router.get("/tools/{name}")
    def tool_detail(name: str) -> dict[str, Any]:
        """One tool's full schema — cheaper than pulling the whole manifest."""
        spec = agent_tools.tool_spec(name)
        if spec is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Unknown tool '{name}'. GET /tools lists the "
                    f"{len(agent_tools.TOOL_SPECS)} available."
                ),
            )
        return spec.manifest_entry()

    @router.post("/tools/call")
    async def tools_call(payload: ToolCallRequest) -> Any:
        """Execute one agent tool by name. Errors keep the domain meaning."""
        try:
            return agent_tools.dispatch_tool(service, payload.tool, dict(payload.args))
        except agent_tools.ToolError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except StateConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except RightsNotConfirmedError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    return router
