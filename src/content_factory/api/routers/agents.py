"""Multi-vendor agent catalogue, brief export and result import."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from ...models import (
    AgentCatalog,
    AgentResultCreate,
    Project,
)
from ...service import ContentFactoryService
from ..deps import guard, guard_value


def build_router(service: ContentFactoryService) -> APIRouter:

    router = APIRouter()

    @router.get("/agents", response_model=AgentCatalog)
    async def agent_catalog() -> AgentCatalog:
        """Every AI agent, TTS engine, and script style the pipeline can use."""
        return service.agent_catalog()

    @router.get("/projects/{project_id}/brief.md", response_class=PlainTextResponse)
    async def export_brief(
        project_id: str, agent: str | None = None
    ) -> PlainTextResponse:
        markdown = guard_value(lambda: service.export_brief(project_id, agent=agent))
        return PlainTextResponse(markdown, media_type="text/markdown; charset=utf-8")

    @router.post("/projects/{project_id}/agent-result", response_model=Project)
    async def import_agent_result(project_id: str, data: AgentResultCreate) -> Project:
        return guard(lambda: service.import_agent_result(project_id, data))

    return router
