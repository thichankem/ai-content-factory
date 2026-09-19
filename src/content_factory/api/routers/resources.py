"""Compute-resource endpoints: what this machine is, and what it will do next.

* ``GET /resources``                — hardware, limits, live admission, counters
* ``GET /resources/explain?kind=…`` — what would happen to one job right now

These are deliberately read-only. Nothing here starts, throttles or stops a job:
the governor already does that inside the render, transcribe and OCR paths. The
endpoints exist so an operator — or an external agent about to commit to a long
job — can see the machine instead of inferring it from a slow export.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from ...resources import JobKind
from ...service import ContentFactoryService


def build_router(service: ContentFactoryService) -> APIRouter:

    router = APIRouter()

    @router.get("/resources")
    def resources(
        refresh: bool = Query(
            False, description="Re-probe the hardware instead of using the cache."
        ),
    ) -> dict[str, Any]:
        """Hardware profile, governor limits, per-kind admission and counters."""
        return service.resource_snapshot(refresh=refresh)

    @router.get("/resources/kinds")
    def resource_kinds() -> list[str]:
        """The job kinds the governor schedules."""
        return [str(kind) for kind in JobKind]

    @router.get("/resources/explain")
    def resource_explain(
        kind: str = Query(..., description="render | transcribe | ocr | vision"),
    ) -> dict[str, Any]:
        """What would happen to this job right now, without starting it."""
        try:
            return service.resource_explain(kind)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    return router
