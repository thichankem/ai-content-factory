"""Image (Photoshop-style) and voice (Audition-style) studio."""

from __future__ import annotations

from typing import Any

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    Query,
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

    # Read-only describe endpoints are registered for both GET and POST: GET is
    # the honest method for a lookup, POST keeps every existing client (and the
    # frontend, which posts a form) working. The bodies live in these helpers so
    # the two methods can never answer differently.
    def _describe_video_op(name: str) -> dict[str, Any]:
        try:
            return service.describe_video_operation(name)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    def _describe_audio_op(name: str) -> dict[str, Any]:
        try:
            return service.describe_audio_operation(name)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.get("/studio/image/presets")
    def image_presets() -> dict[str, Any]:
        """Named one-click photo looks and the raw op vocabulary."""
        from ...image_engine import KNOWN_FILTERS, KNOWN_OPS

        return {
            "presets": service.image_presets(),
            "ops": KNOWN_OPS,
            "filters": KNOWN_FILTERS,
        }

    @router.get("/studio/image/ops")
    def image_ops_catalog() -> dict[str, Any]:
        """Full op catalogue grouped by category, with plain-language docs."""
        return service.image_op_catalog()

    # --- video & audio effects + accessibility -------------------------------

    @router.get("/studio/video/effects")
    def video_effects_catalog() -> dict[str, Any]:
        """Every video frame effect with a plain-language description."""
        return service.video_effect_catalog()

    @router.post("/studio/video/effect")
    async def apply_video_effect_studio(
        file: UploadFile = File(...),  # noqa: B008
        name: str = Form(...),
        params: str | None = Form(None),
        format: str = Form("png"),
    ) -> dict[str, Any]:
        """Apply a frame effect to an image (or a video frame)."""
        import json as _json

        data = await file.read()
        parsed = _json.loads(params) if params else None
        try:
            return service.apply_video_effect(data, name, parsed, export_format=format)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.get("/studio/audio/effects")
    def audio_effects_catalog() -> dict[str, Any]:
        """Every audio effect with a plain-language description."""
        return service.audio_effect_catalog()

    @router.post("/studio/audio/effect")
    async def apply_audio_effect_studio(
        file: UploadFile = File(...),  # noqa: B008
        name: str = Form(...),
        params: str | None = Form(None),
        format: str = Form("mp3"),
    ) -> dict[str, Any]:
        """Apply a DSP effect to audio bytes."""
        import json as _json

        data = await file.read()
        parsed = _json.loads(params) if params else None
        try:
            return service.apply_audio_effect(data, name, parsed, export_format=format)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.post("/studio/audio/analyze")
    async def analyze_audio_studio(file: UploadFile = File(...)) -> dict[str, Any]:  # noqa: B008
        """Measure an audio clip: waveform, spectrogram, frequency, meters."""
        data = await file.read()
        try:
            return service.analyze_audio(data)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.get("/studio/audio/sfx")
    def sfx_catalog_studio() -> dict[str, Any]:
        """Every synthesised sound effect with a plain-language description."""
        return service.sfx_catalog()

    @router.post("/studio/audio/sfx")
    def synthesize_sfx_studio(
        name: str = Form(...),
        params: str | None = Form(None),
        format: str = Form("wav"),
    ) -> dict[str, Any]:
        """Generate a sound effect from scratch and persist it."""
        import json as _json

        parsed = _json.loads(params) if params else None
        try:
            return service.synthesize_sfx(name, parsed, export_format=format)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.get("/studio/audio/ops")
    def audio_ops_catalog() -> dict[str, Any]:
        """Every audio operation grouped by category, with descriptions."""
        return service.audio_operation_catalog()

    @router.get("/studio/audio/describe-op")
    def describe_audio_op_get(
        name: str = Query(..., description="Operation name from /studio/audio/ops."),
    ) -> dict[str, Any]:
        """Explain one audio operation in plain language (read-only)."""
        return _describe_audio_op(name)

    @router.post("/studio/audio/describe-op")
    def describe_audio_op_studio(
        name: str = Form(...),
    ) -> dict[str, Any]:
        """Explain one audio operation in plain language (form-encoded form)."""
        return _describe_audio_op(name)

    @router.post("/studio/audio/describe")
    async def describe_audio_studio(file: UploadFile = File(...)) -> dict[str, Any]:  # noqa: B008
        """Describe an audio clip in plain language from its measurements."""
        data = await file.read()
        try:
            return service.describe_audio(data)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.post("/studio/audio/mastering")
    async def suggest_audio_mastering_studio(
        file: UploadFile = File(...),  # noqa: B008
    ) -> dict[str, Any]:
        """Auto-suggest a mastering chain from the audio measurements."""
        data = await file.read()
        try:
            return service.suggest_audio_mastering(data)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.post("/studio/audio/mastering/apply")
    async def apply_audio_mastering_studio(
        file: UploadFile = File(...),  # noqa: B008
        format: str = Form("wav"),
    ) -> dict[str, Any]:
        """Run the auto-suggested mastering chain and persist the mastered audio."""
        data = await file.read()
        try:
            return service.apply_audio_mastering(data, export_format=format)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.get("/studio/audio/ai")
    def ai_audio_catalog_studio() -> dict[str, Any]:
        """Every AI audio capability with a plain-language description."""
        return service.ai_audio_catalog()

    @router.post("/studio/audio/dub")
    async def dub_audio_studio(
        file: UploadFile = File(...),  # noqa: B008
        target_text: str = Form(...),
        lang: str = Form("en"),
    ) -> dict[str, Any]:
        """Dub a clip via a registered ML adapter (raises if none configured)."""
        data = await file.read()
        try:
            return service.dub_audio(data, target_text, lang)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.post("/studio/audio/voice-clone")
    async def voice_clone_studio(
        file: UploadFile = File(...),  # noqa: B008
        ref_voice: UploadFile = File(...),  # noqa: B008
    ) -> dict[str, Any]:
        """Clone a voice via a registered ML adapter (raises if none configured)."""
        data = await file.read()
        ref = await ref_voice.read()
        try:
            return service.voice_clone(data, ref)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.get("/studio/audio/stems")
    def stem_catalog_studio() -> dict[str, Any]:
        """Every available audio stem with a plain-language description."""
        return service.stem_catalog()

    @router.post("/studio/audio/stems")
    async def separate_audio_stems_studio(
        file: UploadFile = File(...),  # noqa: B008
        num: int = Form(2),
        format: str = Form("wav"),
    ) -> dict[str, Any]:
        """Separate a mono clip into stems (voice/instrumental or low/mid/high)."""
        data = await file.read()
        try:
            return service.separate_audio_stems(data, num, export_format=format)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.get("/studio/video/ops")
    def video_ops_catalog() -> dict[str, Any]:
        """Every video/audio operation grouped by category, with descriptions."""
        return service.video_operation_catalog()

    @router.get("/studio/video/describe-op")
    def describe_video_op_get(
        name: str = Query(..., description="Operation name from /studio/video/ops."),
    ) -> dict[str, Any]:
        """Explain one video/audio operation in plain language (read-only)."""
        return _describe_video_op(name)

    @router.post("/studio/video/describe-op")
    def describe_video_op_studio(
        name: str = Form(...),
    ) -> dict[str, Any]:
        """Explain one video/audio operation in plain language (form-encoded)."""
        return _describe_video_op(name)

    @router.get("/projects/{project_id}/timeline/describe")
    def describe_video_timeline_studio(project_id: str) -> dict[str, Any]:
        """Summarise a project's timeline in natural language."""
        try:
            return service.describe_video_timeline(project_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.get("/projects/{project_id}/timeline/suggest")
    def suggest_video_edits_studio(project_id: str) -> dict[str, Any]:
        """Turn the timeline report into concrete edit suggestions."""
        try:
            return service.suggest_video_edits(project_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.post("/studio/image/analyze")
    async def analyze_image_studio(file: UploadFile = File(...)) -> dict[str, Any]:  # noqa: B008
        """Describe an image from its pixel statistics (vision-free)."""
        data = await file.read()
        return service.analyze_image(data)

    @router.post("/studio/image/suggest")
    async def suggest_image_studio(file: UploadFile = File(...)) -> dict[str, Any]:  # noqa: B008
        """Histogram-based auto-suggestions for an image."""
        data = await file.read()
        return service.suggest_image_edits(data)

    @router.get("/studio/image/describe-op")
    def describe_image_op_get(
        name: str = Query(..., description="Op name from /studio/image/ops."),
        params: str | None = Query(
            None, description="Optional op parameters as a JSON object string."
        ),
    ) -> dict[str, Any]:
        """Explain a single image op in plain language (read-only)."""
        return _describe_image_op(name, params)

    @router.post("/studio/image/describe-op")
    def describe_image_op_studio(
        name: str = Form(...),
        params: str | None = Form(None),
    ) -> dict[str, Any]:
        """Explain a single op in plain language (form-encoded)."""
        return _describe_image_op(name, params)

    def _describe_image_op(name: str, params: str | None) -> dict[str, Any]:
        import json as _json

        parsed = _json.loads(params) if params else None
        try:
            return service.describe_image_op(name, parsed)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.post("/studio/image/batch")
    async def batch_edit_image_studio(
        files: list[UploadFile] = File(...),  # noqa: B008
        ops: str | None = Form(None),
        preset: str | None = Form(None),
        format: str = Form("png"),
    ) -> dict[str, Any]:
        """Apply the same pipeline to several images (batch / sync settings)."""
        import json as _json

        if not files:
            raise HTTPException(
                status_code=422, detail="At least one file is required."
            )
        parsed_ops = _json.loads(ops) if ops else None
        datas = [await f.read() for f in files]
        try:
            return service.batch_edit_image(
                datas, ops=parsed_ops, preset=preset, export_format=format
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.post("/studio/image/session/begin")
    async def begin_image_session_studio(
        file: UploadFile = File(...),  # noqa: B008
    ) -> dict[str, Any]:
        """Start a non-destructive edit session around an image."""
        data = await file.read()
        try:
            return service.begin_image_session(data)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.post("/studio/image/session/{session_id}/edit")
    async def edit_image_session_studio(
        session_id: str,
        ops: str = Form(...),
        format: str = Form("png"),
    ) -> dict[str, Any]:
        """Apply a step to a session and record it in the undo stack."""
        import json as _json

        try:
            parsed = _json.loads(ops)
            return service.edit_image_session(session_id, parsed, export_format=format)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.post("/studio/image/session/{session_id}/undo")
    def undo_image_session_studio(
        session_id: str,
        format: str = Form("png"),
    ) -> dict[str, Any]:
        """Undo the last edit step."""
        try:
            return service.undo_image_session(session_id, export_format=format)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.post("/studio/image/session/{session_id}/redo")
    def redo_image_session_studio(
        session_id: str,
        format: str = Form("png"),
    ) -> dict[str, Any]:
        """Redo the last undone edit step."""
        try:
            return service.redo_image_session(session_id, export_format=format)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.get("/studio/image/session/{session_id}")
    def image_session_state_studio(session_id: str) -> dict[str, Any]:
        """Current state of a session (version, undo/redo availability)."""
        try:
            return service.image_session_state(session_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

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
