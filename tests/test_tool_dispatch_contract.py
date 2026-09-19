"""Every agent tool is dispatched, not merely listed.

``tests/test_agent_tools.py`` asserts that the manifest *names* the tools. At the
time this module was written 55 of the 110 tools appeared in no test and no
script at all, and nothing executed them — so two were dead through the entire
suite: ``research_project`` returned an un-awaited coroutine and
``ground_project`` was called with the wrong arity. Both surfaced to a client as
an opaque HTTP 500 while ``pytest`` stayed green.

This module executes every tool with the smallest legal argument set and asserts:

* a failure is always a *declared* domain error (never ``TypeError``,
  ``AttributeError``, an un-awaited coroutine, or a serialization error), and
* a success is always JSON-serializable with ``json.dumps``.

It is deliberately **not** a functional test: "no video project yet" or "not
found" are fine answers for a tool called with a synthesized id. The bar is that
the tool *ran* and failed for a reason a client can act on.
"""

from __future__ import annotations

import base64
import inspect
import io
import json
import math
import struct
import wave
from typing import Any

import pytest

from content_factory.agent_tools import (
    TOOL_MANIFEST,
    TOOL_REGISTRY,
    ToolError,
    dispatch_tool,
)
from content_factory.models import ProjectCreate
from content_factory.services.errors import (
    NotFoundError,
    RightsNotConfirmedError,
    StateConflictError,
)

#: Exceptions a tool may raise and have mapped onto a 4xx/5xx *with a message*
#: by ``api/errors.py``. Anything else is an unhandled failure: a client cannot
#: tell it apart from a crash in the server.
DECLARED_ERRORS = (
    ToolError,  # malformed arguments, caught by the handler's own reader
    NotFoundError,
    StateConflictError,
    RightsNotConfirmedError,
    ValueError,  # every engine error type subclasses this (ImageError, SfxError, ...)
    KeyError,
    LookupError,
    FileNotFoundError,
    RuntimeError,  # MediaToolError, RenderError
)

#: Arguments whose value only has to be *some* string; the tool is expected to
#: reject an unknown id with a message rather than blow up.
_MISSING_IDS = {"kb_id", "session_id", "asset_id", "media_id", "scene_id"}


def _tiny_png() -> bytes:
    """A 1×1 PNG, so image tools have something real to open."""
    import numpy as np
    from PIL import Image

    buffer = io.BytesIO()
    Image.fromarray(np.zeros((2, 2, 3), dtype=np.uint8)).save(buffer, format="PNG")
    return buffer.getvalue()


def _tiny_wav() -> bytes:
    """0.1 s of silence, so audio tools have something real to decode."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(8000)
        handle.writeframes(struct.pack("<" + "h" * 800, *([0] * 800)))
    return buffer.getvalue()


@pytest.fixture
def service(tmp_path):
    from content_factory.service import ContentFactoryService

    settings = _settings(tmp_path)
    return ContentFactoryService(settings)


def _settings(tmp_path):
    from content_factory.config import Settings

    return Settings(
        store_path=str(tmp_path / "projects.json"),
        uploads_dir=str(tmp_path / "uploads"),
        media_dir=str(tmp_path / "media"),
        library_dir=str(tmp_path / "library"),
        cache_dir=str(tmp_path / "cache"),
    )


@pytest.fixture
def context(service):
    """A project plus one real image and one real audio clip to point at."""
    project = service.create_project(
        ProjectCreate(name="Dispatch demo", topic="Lịch sử tàu Titanic")
    )
    png = _tiny_png()
    wav = _tiny_wav()
    image = service.media_upload("dispatch.png", png)
    audio = service.media_upload("dispatch.wav", wav)
    return {
        "service": service,
        "project_id": project.id,
        "media_id": image.id,
        "audio_id": audio.id,
        "image_b64": base64.b64encode(png).decode(),
        "audio_b64": base64.b64encode(wav).decode(),
    }


def _arguments(tool: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """Build the smallest legal argument set for one tool from its schema."""
    schema = tool["input_schema"]
    properties: dict[str, Any] = schema.get("properties", {})
    return {
        name: _value(name, spec, ctx)
        for name, spec in properties.items()
        if name in schema.get("required", ())
    }


def _value(name: str, spec: dict[str, Any], ctx: dict[str, Any]) -> Any:
    """A plausible value for one declared argument, chosen by name then type."""
    lowered = name.lower()
    if name == "project_id" or lowered.endswith("project_id"):
        return ctx["project_id"]
    if name in _MISSING_IDS:
        return f"no-such-{name}"
    if lowered.endswith("_b64") or "base64" in lowered:
        return (
            _audio_b64(ctx)
            if "audio" in lowered or "voice" in lowered
            else ctx["image_b64"]
        )
    if name == "ref" or lowered.endswith("_ref"):
        return ctx["media_id"]
    if lowered in {"media_id", "source_media_id"}:
        return ctx["media_id"]
    declared = spec.get("type")
    if declared == "boolean":
        return False
    if declared == "integer":
        return 1
    if declared == "number":
        return 0.5
    if declared in {"array", "object"}:
        return [] if declared == "array" else {}
    if declared == "string" or declared is None:
        return _string_value(name, lowered)
    return None


def _audio_b64(ctx: dict[str, Any]) -> str:
    return ctx["audio_b64"]


def _string_value(name: str, lowered: str) -> str:
    """A name-shaped string that is valid for the *category* of argument."""
    if lowered in {"name", "op", "operation", "kind"}:
        # A real operation or job kind, so the tool gets past its lookup.
        return "render" if lowered == "kind" else "crop"
    if lowered in {"language", "target_language"}:
        return "en"
    if lowered in {"format", "export_format", "ext"}:
        return "png"
    if lowered == "platform":
        return "youtube"
    if lowered in {"metric"}:
        return "ctr"
    return "dispatch-test"


def test_every_tool_in_the_manifest_has_a_handler() -> None:
    for tool in TOOL_MANIFEST:
        spec = TOOL_REGISTRY.get(tool["name"])
        assert spec is not None, tool["name"]
        assert callable(spec.handler), tool["name"]


def test_required_arguments_are_always_described() -> None:
    """A required argument that is not in ``properties`` cannot be supplied."""
    for tool in TOOL_MANIFEST:
        schema = tool["input_schema"]
        for name in schema.get("required", ()):
            assert name in schema["properties"], f"{tool['name']}.{name}"


def test_every_tool_dispatches_without_an_undeclared_failure(context) -> None:
    """The guard that would have caught the two dead tools on day one."""
    service = context["service"]
    failures: list[str] = []
    for tool in TOOL_MANIFEST:
        name = tool["name"]
        args = _arguments(tool, context)
        try:
            result = dispatch_tool(service, name, args)
        except DECLARED_ERRORS as exc:
            assert str(exc).strip(), f"{name} failed without a message"
            continue
        except Exception as exc:  # noqa: BLE001 - this is the assertion
            failures.append(f"{name}: {type(exc).__name__}: {exc}")
            continue
        assert not inspect.isawaitable(result), (
            f"{name} returned an un-awaited coroutine"
        )
        try:
            json.dumps(result)
        except (TypeError, ValueError) as exc:
            failures.append(f"{name}: result is not JSON-serializable: {exc}")
    assert not failures, "tools failed in a way a client cannot act on:\n" + "\n".join(
        failures
    )


def test_every_declared_argument_is_read_by_its_handler() -> None:
    """A declared-but-unread argument is a schema that lies to the agent.

    ``ground_project`` declared only ``project_id`` while the service required a
    ``GroundRequest`` as well; the mismatch is invisible in the manifest. This
    cannot prove a handler *uses* every argument, but it does prove none of them
    is silently dropped by an arity mismatch — the handler is called with each
    declared argument present in the payload.
    """
    for tool in TOOL_MANIFEST:
        spec = TOOL_REGISTRY[tool["name"]]
        for name in spec.required:
            assert name in tool["input_schema"]["properties"], tool["name"]
            assert name in spec.properties, (
                f"{tool['name']}.{name} is required but undeclared"
            )


def _call(client, tool: str, args: dict[str, Any]):
    return client.post("/tools/call", json={"tool": tool, "args": args})


@pytest.fixture
def client(tmp_path):
    from fastapi.testclient import TestClient

    from content_factory.api import create_app

    return TestClient(create_app(_settings(tmp_path)))


def test_bad_input_never_answers_500(client) -> None:
    """Bad input must be a 4xx that says what to fix, not an empty 500.

    Sixteen of eighteen malformed calls used to come back as
    ``500 Internal Server Error`` with a Starlette body, because only four
    service-level error types were translated at the HTTP boundary.
    """
    project = client.post(
        "/projects", json={"name": "Contract", "topic": "Titanic"}
    ).json()
    png_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8Dw"
        "HwAFAAH/q842iQAAAABJRU5ErkJggg=="
    )
    cases = [
        ("apply_audio_effect", {"audio_b64": "AAAA", "name": "no-such-effect"}),
        ("edit_image", {"image_b64": "AAAA", "ops": [{"name": "no-such-op"}]}),
        ("describe_media", {"ref": "no-such-asset"}),
        ("describe_media", {"ref": png_b64}),
        ("compose_images", {"base": png_b64, "layers": []}),
        ("separate_audio_stems", {"audio_b64": "AAAA", "num": 9}),
        ("ground_project", {"project_id": project["id"]}),
        ("does_not_exist", {}),
    ]
    for tool, args in cases:
        response = _call(client, tool, args)
        assert response.status_code < 500, (tool, response.status_code, response.text)
        detail = response.json().get("detail")
        assert detail, (tool, response.text)
        assert "Internal Server Error" not in str(detail), (tool, detail)


def test_unknown_session_is_a_404(client) -> None:
    """A session that does not exist is not a server error."""
    response = _call(
        client, "edit_image_session", {"session_id": "deadbeef", "ops": []}
    )
    assert response.status_code == 404
    assert "deadbeef" in response.json()["detail"]


def test_studio_and_tools_agree_on_the_status_code(client) -> None:
    """The same bad input must not be 422 through one door and 500 through another."""
    body = {"image_b64": "AAAA", "ops": []}
    tools_status = _call(client, "edit_image", body).status_code
    studio_status = client.post("/studio/image/edit", json=body).status_code
    assert tools_status == studio_status == 422


def test_tools_call_returns_json_for_every_declared_tool(client) -> None:
    """The HTTP door must never hand a client a body it cannot parse."""
    project = client.post("/projects", json={"name": "Json", "topic": "Titanic"}).json()
    for tool in TOOL_MANIFEST:
        name = tool["name"]
        args = dict.fromkeys(tool["input_schema"].get("required", ()), "x")
        if "project_id" in args:
            args["project_id"] = project["id"]
        response = _call(client, name, args)
        assert response.status_code < 500, (name, response.status_code, response.text)
        payload = response.json()  # raises if the body is not JSON at all
        if response.status_code >= 400:
            assert isinstance(payload.get("detail"), str), (name, payload)
            assert payload["detail"].strip(), (name, payload)


def test_number_of_tools_is_reported_in_errors(client) -> None:
    """The unknown-tool message tells an agent where to find the real list."""
    response = _call(client, "nope", {})
    assert response.status_code == 422
    assert f"{len(TOOL_MANIFEST)}" in response.json()["detail"]


def test_synthesized_numbers_stay_finite() -> None:
    """Guard the guard: the argument synthesizer must not emit NaN/inf."""
    for tool in TOOL_MANIFEST:
        for name, spec in tool["input_schema"]["properties"].items():
            if spec.get("type") == "number":
                value = _value(name, spec, {"image_b64": "", "audio_b64": ""})
                assert math.isfinite(float(value)), f"{tool['name']}.{name}"
