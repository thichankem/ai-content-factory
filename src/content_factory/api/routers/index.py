"""Studio single-page application entry point."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from ...service import ContentFactoryService
from ..deps import FRONTEND_DIR


def build_router(service: ContentFactoryService) -> APIRouter:

    router = APIRouter()

    @router.get("/", response_class=HTMLResponse)
    async def index() -> HTMLResponse:
        index_html = FRONTEND_DIR / "index.html"
        return HTMLResponse(index_html.read_text(encoding="utf-8"))

    return router
