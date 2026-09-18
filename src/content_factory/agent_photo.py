"""Photo-analysis and edit-session agent tools, split out of ``agent_tools.py``.

Kept in their own module so ``agent_tools.py`` stays under its line budget
while the registry still exposes the tools through the same manifest (and
therefore through the MCP server's ``factory_call_tool``).
"""

from __future__ import annotations

import base64 as _base64
from typing import Any


def _h_analyze_image(service: Any, args: Any) -> Any:
    return service.analyze_image(args.base64("image_b64"))


def _h_image_op_catalog(service: Any, args: Any) -> Any:
    return service.image_op_catalog()


def _h_describe_image_op(service: Any, args: Any) -> Any:
    return service.describe_image_op(
        args.string("name"), args.mapping("params") or None
    )


def _h_suggest_image_edits(service: Any, args: Any) -> Any:
    return service.suggest_image_edits(args.base64("image_b64"))


def _h_batch_edit_image(service: Any, args: Any) -> Any:
    datas = [_base64.b64decode(item) for item in args.strings("images_b64")]
    return service.batch_edit_image(
        datas,
        ops=args.objects("ops"),
        preset=args.optional_string("preset"),
        export_format=args.string("format", "png"),
    )


def _h_begin_image_session(service: Any, args: Any) -> Any:
    return service.begin_image_session(args.base64("image_b64"))


def _h_edit_image_session(service: Any, args: Any) -> Any:
    return service.edit_image_session(
        args.string("session_id"),
        args.objects("ops"),
        export_format=args.string("format", "png"),
    )


def _h_undo_image_session(service: Any, args: Any) -> Any:
    return service.undo_image_session(
        args.string("session_id"), export_format=args.string("format", "png")
    )


def _h_redo_image_session(service: Any, args: Any) -> Any:
    return service.redo_image_session(
        args.string("session_id"), export_format=args.string("format", "png")
    )


def _h_image_session_state(service: Any, args: Any) -> Any:
    return service.image_session_state(args.string("session_id"))


def photo_tool_specs() -> list[Any]:
    """Build the photo tool specs (lazy import to avoid a cycle)."""
    from .agent_tools import ToolSpec, _p

    return [
        ToolSpec(
            "analyze_image",
            "Describe an image from its pixel statistics (brightness, contrast, "
            "colour cast, saturation, sharpness) — works without a vision model.",
            "image",
            "analyze_image",
            _h_analyze_image,
            {"image_b64": _p("string", "Base64 of a png/jpeg/webp image.")},
            ("image_b64",),
        ),
        ToolSpec(
            "image_op_catalog",
            "List every photo operation grouped by category, with plain-language "
            "descriptions of what each one does.",
            "image",
            "image_op_catalog",
            _h_image_op_catalog,
        ),
        ToolSpec(
            "describe_image_op",
            "Explain one photo operation in plain language, with its parameters.",
            "image",
            "describe_image_op",
            _h_describe_image_op,
            {
                "name": _p("string", "The op name, e.g. exposure."),
                "params": _p("object", "Optional parameter values to echo back."),
            },
            ("name",),
        ),
        ToolSpec(
            "suggest_image_edits",
            "Suggest a starting edit recipe for an image from its histogram.",
            "image",
            "suggest_image_edits",
            _h_suggest_image_edits,
            {"image_b64": _p("string", "Base64 of a png/jpeg/webp image.")},
            ("image_b64",),
        ),
        ToolSpec(
            "batch_edit_image",
            "Apply the same op pipeline to several images at once.",
            "image",
            "batch_edit_image",
            _h_batch_edit_image,
            {
                "images_b64": _p(
                    "array", "Base64 images, in order.", items=_p("string", "")
                ),
                "ops": _p(
                    "array",
                    "Ops to apply to every image.",
                    items=_p("object", "{name, params}"),
                ),
                "preset": _p("string", "Optional named look."),
                "format": _p("string", "png, jpeg or webp."),
            },
            ("images_b64",),
        ),
        ToolSpec(
            "begin_image_session",
            "Start a non-destructive edit session around an image (enables undo/redo).",
            "image",
            "begin_image_session",
            _h_begin_image_session,
            {"image_b64": _p("string", "Base64 of a png/jpeg/webp image.")},
            ("image_b64",),
        ),
        ToolSpec(
            "edit_image_session",
            "Apply an op step to an edit session and record it in the undo stack.",
            "image",
            "edit_image_session",
            _h_edit_image_session,
            {
                "session_id": _p("string", "The session id from begin_image_session."),
                "ops": _p(
                    "array",
                    "Ops to apply as one step.",
                    items=_p("object", "{name, params}"),
                ),
                "format": _p("string", "png, jpeg or webp."),
            },
            ("session_id", "ops"),
        ),
        ToolSpec(
            "undo_image_session",
            "Undo the last edit step of an image session.",
            "image",
            "undo_image_session",
            _h_undo_image_session,
            {"session_id": _p("string", "The session id.")},
            ("session_id",),
        ),
        ToolSpec(
            "redo_image_session",
            "Redo the last undone edit step of an image session.",
            "image",
            "redo_image_session",
            _h_redo_image_session,
            {"session_id": _p("string", "The session id.")},
            ("session_id",),
        ),
        ToolSpec(
            "image_session_state",
            "Current undo/redo state of an image edit session.",
            "image",
            "image_session_state",
            _h_image_session_state,
            {"session_id": _p("string", "The session id.")},
            ("session_id",),
        ),
    ]
