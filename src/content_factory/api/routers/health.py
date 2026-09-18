"""Health and readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from ... import __version__
from ...config import Settings
from ...models import HealthResponse
from ...service import ContentFactoryService


def build_router(service: ContentFactoryService, settings: Settings) -> APIRouter:

    router = APIRouter()

    @router.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            app=settings.app_name,
            version=__version__,
            providers=service.providers.health(),
        )

    return router
