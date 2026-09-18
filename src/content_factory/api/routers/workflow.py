"""Drag-and-drop production flow (DAG) endpoints."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from ...models import (
    Project,
    Workflow,
    WorkflowChecklist,
    WorkflowRun,
    WorkflowRunRequest,
    WorkflowSave,
)
from ...service import (
    ContentFactoryService,
    NotFoundError,
    StateConflictError,
)
from ...workflow import WorkflowChecklistError
from ..deps import get_or_404, guard_await, guard_value


def build_router(service: ContentFactoryService) -> APIRouter:

    router = APIRouter()

    @router.get("/workflow/blocks")
    async def workflow_blocks() -> list[dict]:
        """The palette of blocks the flow canvas can drag onto the board."""
        return service.block_catalog()

    @router.get("/projects/{project_id}/workflow", response_model=Workflow)
    async def get_workflow(project_id: str) -> Workflow:
        return guard_value(lambda: service.project_workflow(project_id))

    @router.get(
        "/projects/{project_id}/workflow/checklist", response_model=WorkflowChecklist
    )
    async def get_workflow_checklist(project_id: str) -> WorkflowChecklist:
        """Checklist for the flow as it is stored on the project."""
        return guard_value(lambda: service.workflow_checklist(project_id))

    @router.post(
        "/projects/{project_id}/workflow/checklist", response_model=WorkflowChecklist
    )
    async def validate_workflow(
        project_id: str, data: WorkflowSave
    ) -> WorkflowChecklist:
        """Checklist for a candidate flow, so the canvas can audit unsaved edits."""
        return guard_value(lambda: service.validate_workflow(project_id, data))

    @router.put("/projects/{project_id}/workflow", response_model=Project)
    async def save_workflow(project_id: str, data: WorkflowSave) -> Project:
        try:
            return service.save_workflow(project_id, data)
        except WorkflowChecklistError as exc:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": str(exc),
                    "checklist": exc.checklist.model_dump(mode="json"),
                },
            ) from exc
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except StateConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @router.post("/projects/{project_id}/workflow/run", response_model=WorkflowRun)
    async def run_workflow(
        project_id: str, data: WorkflowRunRequest, background: bool = False
    ) -> WorkflowRun:
        if background:
            return guard_value(lambda: service.start_workflow(project_id, data))
        # The runner is synchronous and drives async pipeline steps with
        # asyncio.run(), which cannot run inside the request's own loop — so a
        # flow run gets its own thread, exactly like the background worker.
        return await guard_await(
            asyncio.to_thread(service.run_workflow, project_id, data)
        )

    @router.get(
        "/projects/{project_id}/workflow/runs", response_model=list[WorkflowRun]
    )
    async def list_workflow_runs(project_id: str, limit: int = 20) -> list[WorkflowRun]:
        get_or_404(service, project_id)
        return service.workflow_runs(project_id, limit=limit)

    @router.get("/workflow/runs/{run_id}", response_model=WorkflowRun)
    async def get_workflow_run(run_id: str) -> WorkflowRun:
        return guard_value(lambda: service.workflow_run(run_id))

    return router
