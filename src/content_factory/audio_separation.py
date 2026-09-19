"""AI audio separation — voice isolation & stem splitting.

Pure NumPy DSP first (deterministic, offline, testable), with a pluggable
adapter hook so a real ML backend (Demucs / Spleeter / UVR) can be dropped in
later without changing the caller. A non-vision agent can separate a clip into
stems and get a plain-language catalog of what is available.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np

from .audio_effects import _biquad, _rbj_coeffs

__all__ = [
    "register_adapter",
    "separate_stems",
    "stem_catalog",
    "voice_isolation",
]

#: Registered ML adapters keyed by stem mode (e.g. "stems2", "voice").
_SEPARATION_ADAPTERS: dict[str, Callable[[np.ndarray, int], dict[str, np.ndarray]]] = {}


def register_adapter(
    mode: str, fn: Callable[[np.ndarray, int], dict[str, np.ndarray]]
) -> None:
    """Register an external ML adapter for a stem mode (e.g. ``"voice"``)."""
    _SEPARATION_ADAPTERS[mode] = fn


def _band(samples: np.ndarray, sr: int, lo: float, hi: float) -> np.ndarray:
    """Band-pass a mono signal between lo..hi Hz using biquads.

    A cascade of a high-pass at ``lo`` and a low-pass at ``hi``: without the
    low-pass the result would keep everything *above* ``hi`` instead of the
    band, which is what this used to do.
    """
    out = _biquad(samples, sr, _rbj_coeffs(lo, sr, "highpass", 0.707))
    return _biquad(out, sr, _rbj_coeffs(hi, sr, "lowpass", 0.707))


def _dsp_separate(samples: np.ndarray, sr: int, num: int) -> dict[str, np.ndarray]:
    """Pure-DSP frequency-band stem split (fallback when no ML adapter)."""
    if num <= 2:
        voice = _band(samples, sr, 200.0, 4000.0)
        return {
            "voice": np.asarray(voice, dtype=np.float32),
            "instrumental": np.asarray(samples - voice, dtype=np.float32),
        }
    low = _biquad(samples, sr, _rbj_coeffs(250.0, sr, "lowpass", 0.707))
    mid = _band(samples, sr, 250.0, 4000.0)
    high = _biquad(samples, sr, _rbj_coeffs(4000.0, sr, "highpass", 0.707))
    return {
        "low": np.asarray(low, dtype=np.float32),
        "mid": np.asarray(mid, dtype=np.float32),
        "high": np.asarray(high, dtype=np.float32),
    }


def separate_stems(
    samples: np.ndarray, sr: int, num: int = 2, mode: str | None = None
) -> dict[str, np.ndarray]:
    """Separate a mono clip into stems.

    Uses a registered ML adapter for ``mode`` when present, otherwise falls back
    to a deterministic DSP band split. ``num=2`` yields voice/instrumental;
    ``num=3`` yields low/mid/high.
    """
    key = mode or (f"stems{num}" if num > 2 else "voice")
    adapter = _SEPARATION_ADAPTERS.get(key) or _SEPARATION_ADAPTERS.get(str(num))
    if adapter is not None:
        return adapter(np.asarray(samples, dtype=np.float32), sr)
    return _dsp_separate(np.asarray(samples, dtype=np.float32), sr, num)


def voice_isolation(samples: np.ndarray, sr: int) -> np.ndarray:
    """Isolate the vocal band of a mono clip."""
    return separate_stems(samples, sr, num=2)["voice"]


_STEM_DOCS: dict[str, str] = {
    "voice": "Isolated vocal band (≈200–4000 Hz).",
    "instrumental": "Everything except the vocal band (music bed / ambience).",
    "low": "Low-frequency stem (bass, kick).",
    "mid": "Mid-frequency stem (vocals, lead instruments).",
    "high": "High-frequency stem (hi-hats, air, cymbals).",
}


def stem_catalog() -> dict[str, Any]:
    """Every available stem with a plain-language description."""
    return {
        "stems": [
            {"name": name, "description": desc, "adapter": name in _SEPARATION_ADAPTERS}
            for name, desc in _STEM_DOCS.items()
        ],
        "adapter_backends": sorted(_SEPARATION_ADAPTERS),
    }
