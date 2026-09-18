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

__all__ = ["ImageVoiceStudio", "IMAGE_PRESETS", "VOICE_PRESETS_DOC"]

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


class ImageVoiceStudio:
    """Persisted image/voice editing operations for a content factory."""

    def __init__(self, library_dir: str | Path) -> None:
        self._dir = Path(library_dir) / "edited"
        self._dir.mkdir(parents=True, exist_ok=True)

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
