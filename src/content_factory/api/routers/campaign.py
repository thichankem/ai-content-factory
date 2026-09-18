"""Multi-format campaign engine endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from ...models import (
    CampaignGenerateRequest,
    MultiFormatCampaign,
    ShortsUpdateRequest,
    ShortsVariant,
)
from ...service import ContentFactoryService
from ..deps import guard_value


def build_router(service: ContentFactoryService) -> APIRouter:

    router = APIRouter()

    @router.post(
        "/projects/{project_id}/campaign/generate",
        response_model=MultiFormatCampaign,
    )
    def generate_campaign(
        project_id: str,
        payload: CampaignGenerateRequest | None = None,
    ) -> MultiFormatCampaign:
        return guard_value(lambda: service.generate_campaign(project_id, payload))

    @router.get("/projects/{project_id}/campaign", response_model=MultiFormatCampaign)
    def get_campaign(project_id: str) -> MultiFormatCampaign:
        return guard_value(lambda: service.get_campaign(project_id))

    @router.put(
        "/projects/{project_id}/campaign/shorts/{short_id}",
        response_model=ShortsVariant,
    )
    def update_short(
        project_id: str,
        short_id: str,
        payload: ShortsUpdateRequest,
    ) -> ShortsVariant:
        return guard_value(lambda: service.update_short(project_id, short_id, payload))

    @router.get("/projects/{project_id}/campaign/export-pack")
    def export_campaign_pack(project_id: str) -> dict[str, Any]:
        return guard_value(lambda: service.export_campaign_pack(project_id))

    return router
