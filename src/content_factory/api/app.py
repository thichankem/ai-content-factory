"""FastAPI application factory for the AI Content Factory."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .. import __version__
from ..config import Settings, get_settings
from ..service import ContentFactoryService
from .deps import FRONTEND_DIR
from .errors import install_handlers
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
    build_resources_router,
    build_seo_router,
    build_skills_router,
    build_studio_media_router,
    build_styles_router,
    build_timeline_router,
    build_tools_router,
    build_workflow_router,
)


def _json_safe(value: Any) -> Any:
    """Coerce a value into something ``json.dumps`` accepts.

    Pydantic validation errors keep the offending exception in ``ctx`` (a
    ``ValueError`` for a failed custom validator, for instance). Those objects
    are not JSON-serialisable, so returning ``exc.errors()`` verbatim used to
    raise ``TypeError`` *inside* the error handler: callers saw an opaque 500
    instead of the 422 that describes what they got wrong. Everything unknown
    therefore degrades to its ``repr`` rather than exploding.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return repr(value)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the application, wiring config, service, and routes together."""
    settings = settings or get_settings()
    service = ContentFactoryService(settings)

    app = FastAPI(title="AI Content Factory", version=__version__)

    # Domain errors from every engine become their own 4xx with a message
    # instead of an empty 500. Installed before the routers so the mapping is
    # in place for all of them.
    install_handlers(app)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        detail = _json_safe(exc.errors())
        return JSONResponse(status_code=422, content={"detail": detail})

    app.include_router(build_health_router(service, settings))
    app.include_router(build_qa_router(service))
    app.include_router(build_resources_router(service))
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
    app.include_router(build_skills_router(service))
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
