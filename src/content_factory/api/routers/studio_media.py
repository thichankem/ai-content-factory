"""Image (Photoshop-style) and voice (Audition-style) studio."""

from __future__ import annotations

from typing import Any

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from fastapi.responses import FileResponse

from ...service import ContentFactoryService

#: Content types for persisted edited assets, by file extension.
_EDITED_MEDIA_TYPES: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
}


def build_router(service: ContentFactoryService) -> APIRouter:

    router = APIRouter()

    @router.get("/studio/image/presets")
    def image_presets() -> dict[str, Any]:
        """Named one-click photo looks and the raw op vocabulary."""
        from ...image_engine import KNOWN_FILTERS, KNOWN_OPS

        return {
            "presets": service.image_presets(),
            "ops": KNOWN_OPS,
            "filters": KNOWN_FILTERS,
        }

    @router.post("/studio/image/edit")
    async def edit_image_studio(
        file: UploadFile = File(...),  # noqa: B008
        ops: str | None = Form(None),
        preset: str | None = Form(None),
        format: str = Form("png"),
    ) -> dict[str, Any]:
        """Edit an image with an ops pipeline (JSON) or a named preset."""
        import json as _json

        data = await file.read()
        parsed_ops = _json.loads(ops) if ops else None
        try:
            return service.edit_image(
                data, ops=parsed_ops, preset=preset, export_format=format
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.get("/studio/voice/presets")
    def voice_presets() -> dict[str, Any]:
        """Named voice chains and every tunable chain parameter."""
        from ...voice_engine import CHAIN_PRESETS, KNOWN_CHAIN_STEPS

        return {
            "presets": service.voice_presets(),
            "chain_params": KNOWN_CHAIN_STEPS,
            "defaults": CHAIN_PRESETS,
        }

    @router.post("/studio/voice/enhance")
    async def enhance_voice_studio(
        file: UploadFile = File(...),  # noqa: B008
        params: str | None = Form(None),
        preset: str | None = Form(None),
        format: str = Form("mp3"),
    ) -> dict[str, Any]:
        """Enhance voice audio through the Audition-style chain."""
        import json as _json

        data = await file.read()
        parsed_params = _json.loads(params) if params else None
        try:
            return service.process_voice_audio(
                data, params=parsed_params, preset=preset, export_format=format
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.get("/edited/{name}")
    def edited_asset(name: str) -> FileResponse:
        """Download a persisted edited asset (image, audio or video)."""
        path = service.edited_asset_path(name)
        return FileResponse(
            path,
            media_type=_EDITED_MEDIA_TYPES.get(
                path.suffix.lower(), "application/octet-stream"
            ),
        )

    return router
