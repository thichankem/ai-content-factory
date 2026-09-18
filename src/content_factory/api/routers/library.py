"""Federated document search and the curated local library."""

from __future__ import annotations

from fastapi import APIRouter

from ...models import (
    DocumentResult,
    LibraryHit,
)
from ...service import ContentFactoryService


def build_router(service: ContentFactoryService) -> APIRouter:

    router = APIRouter()

    @router.get("/documents/search", response_model=list[DocumentResult])
    async def search_documents(q: str, limit: int = 10) -> list[DocumentResult]:
        return await service.search_documents(q, limit=max(1, min(limit, 50)))

    @router.get("/library/search", response_model=list[LibraryHit])
    async def search_library(q: str, limit: int = 20) -> list[LibraryHit]:
        return service.search_library(q, limit=max(1, min(limit, 100)))

    @router.get("/library")
    async def library() -> dict:
        return {
            "documents": service.list_library(),
            "stats": service.library_stats(),
        }

    return router
