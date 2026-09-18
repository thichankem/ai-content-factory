"""Shared HTTP-layer helpers used by every API router.

Routers stay thin: they read the request, call one service method, and let the
helpers here translate a domain error into the matching HTTP response. The
mapping lives in exactly one place (:func:`_http_error`), so a new error type
only has to be taught once.
"""

from __future__ import annotations

import html
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import TypeVar

from fastapi import HTTPException

from ..models import Project
from ..service import (
    ContentFactoryService,
    NotFoundError,
    RightsNotConfirmedError,
    StateConflictError,
)

FRONTEND_DIR = Path(__file__).resolve().parents[3] / "frontend"
T = TypeVar("T")

#: Errors that mean "this action is not valid right now" -> 409.
_CONFLICT_ERRORS = (StateConflictError, RightsNotConfirmedError)
#: Every domain error the HTTP layer knows how to render.
_DOMAIN_ERRORS = (NotFoundError, *_CONFLICT_ERRORS)

#: Detail used by project-scoped endpoints, which deliberately do not echo the
#: service message (it can name internal ids).
PROJECT_NOT_FOUND = "Project not found"


def _http_error(exc: Exception, detail: str | None = None) -> HTTPException:
    """Translate a domain error into the HTTP equivalent."""
    message = detail if detail is not None else str(exc)
    status = 404 if isinstance(exc, NotFoundError) else 409
    return HTTPException(status_code=status, detail=message)


def guard(fn: Callable[[], T]) -> T:
    """Run a project-scoped service call with a generic 404 message."""
    try:
        return fn()
    except NotFoundError as exc:
        raise _http_error(exc, PROJECT_NOT_FOUND) from exc
    except _CONFLICT_ERRORS as exc:
        raise _http_error(exc) from exc


def guard_value(fn: Callable[[], T]) -> T:
    """Run a service call, passing its own error message through to the client."""
    try:
        return fn()
    except _DOMAIN_ERRORS as exc:
        raise _http_error(exc) from exc


async def guard_await(value: Awaitable[T]) -> T:
    """Await a service call, mapping its errors onto HTTP the same way."""
    try:
        return await value
    except _DOMAIN_ERRORS as exc:
        raise _http_error(exc) from exc


def get_or_404(service: ContentFactoryService, project_id: str) -> Project:
    """Load a project or answer 404."""
    try:
        return service.get_project(project_id)
    except NotFoundError as exc:
        raise _http_error(exc, PROJECT_NOT_FOUND) from exc


def render_thumbnail(project: Project) -> str:
    """Render a simple branded SVG placeholder for a produced video."""
    title = html.escape(project.name)
    status = html.escape(project.status.value.replace("_", " "))
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" '
        'viewBox="0 0 640 360">'
        '<rect width="640" height="360" fill="#1a1d27"/>'
        '<rect y="300" width="640" height="60" fill="#6366f1"/>'
        f'<text x="32" y="56" font-family="sans-serif" font-size="20" '
        f'fill="#9aa0b0">{status}</text>'
        f'<text x="32" y="260" font-family="sans-serif" font-size="32" '
        f'fill="#e6e8ee">{title}</text>'
        "</svg>"
    )
