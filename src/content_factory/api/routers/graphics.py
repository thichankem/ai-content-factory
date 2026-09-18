"""Procedural SVG map and infographic generation."""

from __future__ import annotations

from fastapi import APIRouter, Response

from ...models import (
    InfographicSpec,
    MapRouteSpec,
)
from ...service import ContentFactoryService
from ..deps import guard_value


def build_router(service: ContentFactoryService) -> APIRouter:

    router = APIRouter()

    @router.post("/projects/{project_id}/graphics/map")
    def generate_project_map(project_id: str, spec: MapRouteSpec) -> Response:
        """Generate a procedural SVG route/epicenter map."""
        svg = guard_value(lambda: service.generate_map_graphic(project_id, spec))
        return Response(content=svg, media_type="image/svg+xml")

    @router.post("/projects/{project_id}/graphics/infographic")
    def generate_project_infographic(
        project_id: str, spec: InfographicSpec
    ) -> Response:
        """Generate a procedural SVG comparative infographic."""
        svg = guard_value(
            lambda: service.generate_infographic_graphic(project_id, spec)
        )
        return Response(content=svg, media_type="image/svg+xml")

    return router
