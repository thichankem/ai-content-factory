"""Domain-to-HTTP error translation for the whole API surface.

Routers translate the four *service-level* errors themselves (see
``deps.guard``), but the engines below them each publish their own failure
type: ``ImageError``, ``AudioEffectError``, ``SfxError``, ``VideoEffectError``,
``VoiceError``, ``AiAudioError``, ``MediaToolError``, ``RenderError`` ... Those
sailed past every router ``except`` clause, so a bad effect name, an unknown
edit session or a missing adapter reached the client as Starlette's bare
``500 Internal Server Error`` with an empty body — impossible to act on and
indistinguishable from a genuine crash.

The mapping therefore lives here, in one table, and is installed on the
application (:func:`install_handlers`). Every router inherits it, and a new
error type is taught once.

Status codes follow what the caller can do about the failure:

* **404** — the thing named does not exist (unknown id, unknown session, a
  ``KeyError`` from a lookup, a missing file).
* **409** — the request is well-formed but the resource is in the wrong state.
* **413** — the payload is larger than the server accepts.
* **422** — the request itself is wrong: bad effect name, out-of-range
  parameter, a ref where an id was expected.
* **503** — the capability or provider is unavailable; configuring or retrying
  later may work, editing the request will not.
* **500** — the server failed on its own (ffmpeg died, a bug); the body still
  carries the reason instead of being empty.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ..ai_audio import AiAudioError
from ..image_engine import ImageSessionNotFoundError
from ..media import TranscriptionUnavailableError, UploadTooLargeError
from ..media_tools import MediaToolArgumentError, MediaToolError
from ..providers import ProviderError, ProviderUnavailableError
from ..render import RenderError
from ..resilience import CircuitOpenError
from ..service import (
    NotFoundError,
    RightsNotConfirmedError,
    StateConflictError,
)
from ..state import StateMachineError
from ..store import StoreConflictError
from ..workflow import (
    WorkflowBlockedError,
    WorkflowChecklistError,
    WorkflowOrderError,
)

#: The thing named does not exist.
_NOT_FOUND = (NotFoundError, ImageSessionNotFoundError, KeyError, FileNotFoundError)
#: A capability is missing rather than the request being wrong.
_UNAVAILABLE = (
    AiAudioError,
    ProviderUnavailableError,
    CircuitOpenError,
    ProviderError,
    TranscriptionUnavailableError,
)
#: Well-formed request, wrong state for it.
_CONFLICT = (
    StateConflictError,
    RightsNotConfirmedError,
    StoreConflictError,
    WorkflowBlockedError,
)
#: The request is wrong: bad name, bad range, bad argument shape.
_INVALID = (
    MediaToolArgumentError,
    ValueError,  # every engine error type (ImageError, SfxError, ...) subclasses this
    StateMachineError,
    WorkflowChecklistError,
    WorkflowOrderError,
)

#: Ordered ``(exception types, status)`` table; first match wins, so the more
#: specific families must come before ``ValueError`` — which, being the base of
#: most engine errors, belongs near the end.
_STATUS_TABLE: tuple[tuple[tuple[type[BaseException], ...], int], ...] = (
    (_NOT_FOUND, 404),
    ((UploadTooLargeError,), 413),
    (_CONFLICT, 409),
    (_UNAVAILABLE, 503),
    (_INVALID, 422),
    ((MediaToolError, RenderError), 500),
)

#: Handlers are registered for these, so Starlette routes the exception here
#: instead of falling through to a bodyless 500.
HANDLED_ERRORS: tuple[type[BaseException], ...] = (
    NotFoundError,
    ImageSessionNotFoundError,
    KeyError,
    FileNotFoundError,
    UploadTooLargeError,
    *_CONFLICT,
    *_UNAVAILABLE,
    StateMachineError,
    WorkflowChecklistError,
    WorkflowOrderError,
    ValueError,
    MediaToolArgumentError,
    MediaToolError,
    RenderError,
)


def status_for(exc: BaseException) -> int:
    """HTTP status for a domain exception (500 when nothing matches)."""
    for types, status in _STATUS_TABLE:
        if isinstance(exc, types):
            return status
    return 500


def detail_for(exc: BaseException) -> str:
    """Client-facing message for a domain exception.

    ``KeyError`` stringifies as ``"'media_id'"`` — the quotes are noise in an
    API response, so they are stripped. An empty message is never returned: a
    response with no detail is exactly the problem this module exists to fix.
    """
    message = str(exc).strip()
    if isinstance(exc, KeyError) and message.startswith("'") and message.endswith("'"):
        message = message[1:-1]
    return message or exc.__class__.__name__


def install_handlers(app: FastAPI) -> None:
    """Register the domain-error handlers on ``app``.

    ``Exception`` is registered last so anything unmapped still answers with a
    JSON body. Starlette re-raises after responding, so the traceback keeps
    reaching the server log — the body is an improvement, not a silencing.
    """

    async def handle(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status_for(exc),
            content={"detail": detail_for(exc)},
        )

    for error_type in (*HANDLED_ERRORS, Exception):
        app.add_exception_handler(error_type, handle)


__all__ = [
    "HANDLED_ERRORS",
    "detail_for",
    "install_handlers",
    "status_for",
]
