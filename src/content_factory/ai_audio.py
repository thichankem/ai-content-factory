"""AI audio adapters — pluggable ML backends for dubbing & voice cloning.

These features genuinely need a trained model (there is no faithful pure-DSP
equivalent), so the honest contract is a pluggable adapter registry: a caller
registers a backend (e.g. an ElevenLabs/RVC/XTTS integration) and the service
delegates to it; until one is registered the operation fails with a clear
"requires ML adapter" error rather than fabricating a result. A non-vision agent
can still discover what is available via :func:`ai_audio_catalog`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

__all__ = [
    "AiAudioError",
    "ai_audio_catalog",
    "dub_audio",
    "register_adapter",
    "voice_clone",
]

#: Registered ML adapters keyed by capability ("dub", "voice_clone").
_AUDIO_ADAPTERS: dict[str, Callable[..., Any]] = {}


class AiAudioError(ValueError):
    """Raised when an AI audio operation needs an ML adapter that is absent."""


def register_adapter(capability: str, fn: Callable[..., Any]) -> None:
    """Register an external ML adapter for a capability (dub / voice_clone)."""
    _AUDIO_ADAPTERS[capability] = fn


def _require(capability: str) -> Callable[..., Any]:
    adapter = _AUDIO_ADAPTERS.get(capability)
    if adapter is None:
        raise AiAudioError(
            f"'{capability}' needs an ML adapter. Register one via "
            "register_adapter() (e.g. an ElevenLabs / RVC / XTTS integration)."
        )
    return adapter


def dub_audio(
    data: bytes, target_text: str, lang: str = "en", **kwargs: Any
) -> dict[str, Any]:
    """Dub a clip: replace its voice with a spoken rendition of ``target_text``.

    Delegates to a registered ``"dub"`` adapter. Raises :class:`AiAudioError`
    when no adapter is configured.
    """
    if not target_text.strip():
        raise AiAudioError("target_text is required for dubbing.")
    result = _require("dub")(data=data, target_text=target_text, lang=lang, **kwargs)
    return dict(result)


def voice_clone(data: bytes, ref_voice: bytes, **kwargs: Any) -> dict[str, Any]:
    """Clone a voice: re-speak ``data`` in the timbre of ``ref_voice``.

    Delegates to a registered ``"voice_clone"`` adapter. Raises
    :class:`AiAudioError` when no adapter is configured.
    """
    return dict(_require("voice_clone")(data=data, ref_voice=ref_voice, **kwargs))


_CAPABILITY_DOCS: dict[str, dict[str, str]] = {
    "dub": {
        "description": "Replace a clip's voice with a spoken rendition of a "
        "target script (AI dubbing / translation).",
        "requires": "ML adapter (e.g. ElevenLabs dubbing).",
    },
    "voice_clone": {
        "description": "Re-speak audio in the timbre of a reference voice.",
        "requires": "ML adapter (e.g. RVC / XTTS).",
    },
    "separate": {
        "description": "Stem separation / voice isolation (pure DSP fallback "
        "available).",
        "requires": "None (pure DSP).",
    },
}


def ai_audio_catalog() -> dict[str, Any]:
    """Every AI audio capability with a description and adapter status."""
    return {
        "capabilities": [
            {
                "name": name,
                "description": doc["description"],
                "requires": doc["requires"],
                "adapter": name in _AUDIO_ADAPTERS,
            }
            for name, doc in _CAPABILITY_DOCS.items()
        ],
        "registered_adapters": sorted(_AUDIO_ADAPTERS),
    }
