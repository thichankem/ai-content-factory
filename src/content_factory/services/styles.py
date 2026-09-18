"""Reusable narration style presets (the script-style library)."""

from __future__ import annotations

from ..models import ScriptStyle
from .context import ServiceContext


class StylesMixin(ServiceContext):
    """Reusable narration style presets (the script-style library)."""

    # --- Script styles & analysis ---------------------------------------------

    def list_script_styles(self) -> list[ScriptStyle]:
        """Every scripting preset: user files first, then built-ins."""
        return self._presets.list_styles()

    def get_script_style(self, name: str) -> ScriptStyle | None:
        return self._presets.get(name)

    def save_script_style(self, style: ScriptStyle) -> ScriptStyle:
        """Persist a user-tunable preset (JSON, lossless round-trip)."""
        return self._presets.save(style)

    def export_script_style_markdown(self, name: str) -> str | None:
        """Render a preset as Markdown for an external agent to edit."""
        return self._presets.export_markdown(name)

    def delete_script_style(self, name: str) -> bool:
        """Remove a user preset. Built-ins are protected."""
        return self._presets.delete(name)
