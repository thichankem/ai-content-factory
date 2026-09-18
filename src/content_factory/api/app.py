"""FastAPI application factory for the AI Content Factory."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .. import __version__
from ..config import Settings, get_settings
from ..service import ContentFactoryService
from .deps import FRONTEND_DIR
from .routers import (
    build_agents_router,
    build_campaign_router,
    build_external_router,
    build_graphics_router,
    build_health_router,
    build_history_router,
    build_index_router,
    build_knowledge_router,
    build_library_router,
    build_media_router,
    build_projects_router,
    build_qa_router,
    build_seo_router,
    build_studio_media_router,
    build_styles_router,
    build_timeline_router,
    build_tools_router,
    build_workflow_router,
)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the application, wiring config, service, and routes together."""
    settings = settings or get_settings()
    service = ContentFactoryService(settings)

    app = FastAPI(title="AI Content Factory", version=__version__)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    app.include_router(build_health_router(service, settings))
    app.include_router(build_qa_router(service))
    app.include_router(build_seo_router(service))
    app.include_router(build_projects_router(service))
    app.include_router(build_styles_router(service))
    app.include_router(build_agents_router(service))
    app.include_router(build_library_router(service))
    app.include_router(build_timeline_router(service))
    app.include_router(build_workflow_router(service))
    app.include_router(build_campaign_router(service))
    app.include_router(build_knowledge_router(service))
    app.include_router(build_studio_media_router(service))
    app.include_router(build_media_router(service))
    app.include_router(build_tools_router(service))
    app.include_router(build_external_router(service))
    app.include_router(build_history_router(service))
    app.include_router(build_graphics_router(service))
    app.include_router(build_index_router(service))

    uploads_dir = Path("storage/uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

    if FRONTEND_DIR.is_dir():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIR), name="assets")

    return app


app = create_app()
