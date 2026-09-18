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
    def tools_manifest() -> dict[str, Any]:
        """Machine-readable tool manifest so an agent can discover everything."""
        return agent_tools.build_tool_manifest()

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
