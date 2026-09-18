"""Service facade for the image and voice engines.

Sits between the HTTP/agent-tools layer and the pure engines, handling
persistence (edited assets land under ``library/edited/``), preset names,
and JSON-safe reports so every result can be returned directly from an
API endpoint or tool call.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from . import image_engine, voice_engine

__all__ = ["IMAGE_PRESETS", "VOICE_PRESETS_DOC", "ImageVoiceStudio"]

#: One-click photo looks (Photoshop action-style), each an op list.
IMAGE_PRESETS: dict[str, list[dict[str, Any]]] = {
    "thumbnail": [
        {"name": "auto_enhance"},
        {"name": "tone", "params": {"contrast": 1.25, "saturation": 1.3}},
        {"name": "sharpen", "params": {"percent": 80}},
        {"name": "vignette", "params": {"strength": 0.25}},
    ],
    "cinematic": [
        {"name": "curves", "params": {"shadows": 0.06, "highlights": -0.04}},
        {"name": "filter", "params": {"preset": "cool"}},
        {"name": "vignette", "params": {"strength": 0.4}},
    ],
    "noir": [
        {"name": "filter", "params": {"preset": "noir"}},
        {"name": "vignette", "params": {"strength": 0.45}},
        {"name": "sharpen", "params": {"percent": 40}},
    ],
    "clean": [{"name": "auto_enhance"}],
    "square": [{"name": "padding", "params": {"width": 1080, "height": 1080}}],
    "vertical": [{"name": "padding", "params": {"width": 1080, "height": 1920}}],
}

#: Known-good voice chains exposed by name.
VOICE_PRESETS_DOC = sorted(voice_engine.CHAIN_PRESETS)


class _EditSession:
    """A non-destructive edit session: the original bytes plus a stack of ops.

    Because every op is a pure function over the previous image, undo/redo is
    simply re-applying a shorter or longer prefix of the recorded op stack from
    the untouched original. Nothing destructive ever touches the source.
    """

    def __init__(self, data: bytes) -> None:
        self.original: bytes = data
        self.steps: list[list[dict[str, Any]]] = []
        self.index: int = 0

    def current_pipeline(self) -> list[dict[str, Any]]:
        pipeline: list[dict[str, Any]] = []
        for step in self.steps[: self.index]:
            pipeline.extend(step)
        return pipeline

    def can_undo(self) -> bool:
        return self.index > 0

    def can_redo(self) -> bool:
        return self.index < len(self.steps)


class ImageVoiceStudio:
    """Persisted image/voice editing operations for a content factory."""

    def __init__(self, library_dir: str | Path) -> None:
        self._dir = Path(library_dir) / "edited"
        self._dir.mkdir(parents=True, exist_ok=True)
        self._sessions: dict[str, _EditSession] = {}

    # --- image ---------------------------------------------------------------

    def edit_image_bytes(
        self,
        data: bytes,
        *,
        ops: list[dict[str, Any]] | None = None,
        preset: str | None = None,
        export_format: str = "png",
    ) -> dict[str, Any]:
        """Apply ops (or a named preset) and persist the result; return metadata."""
        pipeline: list[dict[str, Any]] = []
        if preset:
            preset = preset.lower()
            if preset not in IMAGE_PRESETS:
                raise image_engine.ImageError(
                    f"Unknown image preset '{preset}'. Known: {sorted(IMAGE_PRESETS)}"
                )
            pipeline.extend(IMAGE_PRESETS[preset])
        pipeline.extend(ops or [])
        final = image_engine.apply_ops(data, pipeline)
        blob = image_engine.export_bytes(final, export_format)
        asset_id = uuid.uuid4().hex[:12]
        path = self._dir / f"{asset_id}.{export_format.lower().lstrip('.')}"
        path.write_bytes(blob)
        return {
            "asset_id": asset_id,
            "url": f"/edited/{path.name}",
            "format": export_format,
            "width": final.width,
            "height": final.height,
            "size_bytes": len(blob),
            "ops_applied": [entry.get("name", "?") for entry in pipeline],
            "preset": preset,
        }

    # --- analysis & accessibility -------------------------------------------

    def analyze_image_bytes(self, data: bytes) -> dict[str, Any]:
        """Describe an image and suggest edits from its pixel statistics."""
        from . import photo_assist

        img = image_engine.load_image(data)
        return photo_assist.describe_image(img)

    def image_op_catalog(self) -> dict[str, Any]:
        """Full op catalogue grouped by category, with plain-language docs."""
        from . import photo_assist

        return photo_assist.catalog()

    def describe_image_op(
        self, name: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Explain a single op in plain language."""
        from . import photo_assist

        return photo_assist.describe_op(name, params)

    def suggest_image_edits(self, data: bytes) -> dict[str, Any]:
        """Histogram-based auto-suggestions for an image."""
        from . import photo_assist

        img = image_engine.load_image(data)
        return photo_assist.suggest_edits(img)

    def batch_edit_images(
        self,
        images: list[bytes],
        *,
        ops: list[dict[str, Any]] | None = None,
        preset: str | None = None,
        export_format: str = "png",
    ) -> dict[str, Any]:
        """Apply the same pipeline to several images (batch / sync settings)."""
        results = [
            self.edit_image_bytes(
                data, ops=ops, preset=preset, export_format=export_format
            )
            for data in images
        ]
        return {"count": len(results), "results": results}

    # --- non-destructive edit sessions (undo / redo / history) ---------------

    def begin_image_session(self, data: bytes) -> dict[str, Any]:
        """Start a non-destructive edit session around an image."""
        session_id = uuid.uuid4().hex[:12]
        img = image_engine.load_image(data)
        self._sessions[session_id] = _EditSession(data)
        return {
            "session_id": session_id,
            "width": img.width,
            "height": img.height,
            "version": 0,
            "can_undo": False,
            "can_redo": False,
        }

    def edit_image_session(
        self,
        session_id: str,
        ops: list[dict[str, Any]],
        *,
        export_format: str = "png",
    ) -> dict[str, Any]:
        """Apply a step to a session and record it in the undo stack."""
        session = self._require_session(session_id)
        session.steps = session.steps[: session.index]  # drop redo tail
        session.steps.append(ops)
        session.index += 1
        return self._render_session(session, export_format)

    def undo_image_session(
        self, session_id: str, *, export_format: str = "png"
    ) -> dict[str, Any]:
        """Undo the last edit step."""
        session = self._require_session(session_id)
        if not session.can_undo():
            raise image_engine.ImageError("Nothing to undo.")
        session.index -= 1
        return self._render_session(session, export_format)

    def redo_image_session(
        self, session_id: str, *, export_format: str = "png"
    ) -> dict[str, Any]:
        """Redo the last undone edit step."""
        session = self._require_session(session_id)
        if not session.can_redo():
            raise image_engine.ImageError("Nothing to redo.")
        session.index += 1
        return self._render_session(session, export_format)

    def image_session_state(self, session_id: str) -> dict[str, Any]:
        """Current state of a session (version, undo/redo availability)."""
        session = self._require_session(session_id)
        img = image_engine.load_image(session.original)
        return {
            "session_id": session_id,
            "width": img.width,
            "height": img.height,
            "version": session.index,
            "steps": len(session.steps),
            "can_undo": session.can_undo(),
            "can_redo": session.can_redo(),
        }

    def _require_session(self, session_id: str) -> _EditSession:
        session = self._sessions.get(session_id)
        if session is None:
            raise image_engine.ImageError(f"Unknown image session '{session_id}'.")
        return session

    def _render_session(
        self, session: _EditSession, export_format: str
    ) -> dict[str, Any]:
        final = image_engine.apply_ops(session.original, session.current_pipeline())
        blob = image_engine.export_bytes(final, export_format)
        asset_id = uuid.uuid4().hex[:12]
        path = self._dir / f"{asset_id}.{export_format.lower().lstrip('.')}"
        path.write_bytes(blob)
        return {
            "asset_id": asset_id,
            "url": f"/edited/{path.name}",
            "format": export_format,
            "width": final.width,
            "height": final.height,
            "size_bytes": len(blob),
            "version": session.index,
            "can_undo": session.can_undo(),
            "can_redo": session.can_redo(),
            "ops_applied": [
                entry.get("name", "?")
                for step in session.steps[: session.index]
                for entry in step
            ],
        }

    # --- voice ---------------------------------------------------------------

    def process_voice_bytes(
        self,
        data: bytes,
        *,
        params: dict[str, Any] | None = None,
        preset: str | None = None,
        export_format: str = "mp3",
    ) -> dict[str, Any]:
        """Run the Audition-style chain and persist the result."""
        audio, report = voice_engine.process_voice(
            data, params=params, preset=preset, export_format=export_format
        )
        asset_id = uuid.uuid4().hex[:12]
        path = self._dir / f"{asset_id}.{export_format}"
        path.write_bytes(audio)
        report["asset_id"] = asset_id
        report["url"] = f"/edited/{path.name}"
        report["size_bytes"] = len(audio)
        return report

    def persist_audio_bytes(
        self, data: bytes, export_format: str = "mp3"
    ) -> dict[str, Any]:
        """Persist already-encoded audio bytes as an edited asset."""
        fmt = export_format.lower().lstrip(".")
        asset_id = uuid.uuid4().hex[:12]
        path = self._dir / f"{asset_id}.{fmt}"
        path.write_bytes(data)
        return {
            "asset_id": asset_id,
            "url": f"/edited/{path.name}",
            "format": fmt,
            "size_bytes": len(data),
        }

    def duck_music_bytes(
        self, voice: bytes, music: bytes, *, duck_db: float = -12.0
    ) -> dict[str, Any]:
        """Mix a ducked music bed under a voice track."""
        audio = voice_engine.duck_music(voice, music, duck_db=duck_db)
        asset_id = uuid.uuid4().hex[:12]
        path = self._dir / f"{asset_id}.mp3"
        path.write_bytes(audio)
        return {
            "asset_id": asset_id,
            "url": f"/edited/{path.name}",
            "size_bytes": len(audio),
            "duck_db": duck_db,
        }

    def asset_path(self, name: str) -> Path:
        """Resolve an edited asset name safely (no path traversal)."""
        safe = Path(name).name
        path = self._dir / safe
        if not path.is_file():
            raise FileNotFoundError(f"No edited asset '{safe}'.")
        return path
