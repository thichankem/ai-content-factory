"""Sound-effect synthesis — pure NumPy, offline, no samples needed.

Generates the common short SFX an editor reaches for (whoosh, impact,
explosion, footstep, ambience, transition swell, UI clicks) from scratch, so a
text-only agent can drop a sound onto the timeline without hunting for a file.
Each generator returns float32 mono PCM plus a plain-language description for
the accessibility layer.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

__all__ = [
    "SFX",
    "sfx_catalog",
    "synthesize_sfx",
]


class SfxError(ValueError):
    """Raised when an SFX cannot be synthesised."""


def _seed(params: dict[str, Any]) -> int:
    try:
        return int(params.get("seed", 0))
    except (TypeError, ValueError):
        return 0


def _t(sr: int, duration: float) -> np.ndarray:
    return np.arange(int(sr * duration), dtype=np.float32) / sr


def _env_ar(samples: np.ndarray, sr: int, attack: float, release: float) -> np.ndarray:
    """Linear attack/release amplitude envelope."""
    n = len(samples)
    a = max(1, int(sr * attack))
    r = max(1, int(sr * release))
    env = np.ones(n, dtype=np.float32)
    if a < n:
        env[:a] = np.linspace(0.0, 1.0, a)
    if r < n:
        env[-r:] = np.linspace(1.0, 0.0, r)
    return samples * env


def _gen_whoosh(sr: int, params: dict[str, Any]) -> np.ndarray:
    """Filtered noise sweep rising then falling."""
    duration = _num(params, "duration", 0.6)
    rng = np.random.default_rng(_seed(params))
    noise = rng.normal(0.0, 0.6, int(sr * duration)).astype(np.float32)
    t = _t(sr, duration)
    # Band-limit the noise with a fixed moving average.
    window = max(1, int(sr * 0.03))
    kernel = np.ones(window) / window
    smooth = np.convolve(noise, kernel, mode="same")
    # Rising-then-falling amplitude envelope.
    env = np.sin(math.pi * np.clip(t / duration, 0.0, 1.0)) ** 2
    return np.asarray(smooth * env, dtype=np.float32)


def _gen_impact(sr: int, params: dict[str, Any]) -> np.ndarray:
    """A short percussive thump: decaying sine burst + noise click."""
    duration = _num(params, "duration", 0.25)
    freq = _num(params, "freq", 90.0)
    t = _t(sr, duration)
    body = np.sin(2 * np.pi * freq * t) * np.exp(-t * 18.0)
    rng = np.random.default_rng(_seed(params))
    click = rng.normal(0.0, 0.5, len(t)).astype(np.float32) * np.exp(-t * 60.0)
    return np.asarray(body * 0.8 + click * 0.5, dtype=np.float32)


def _gen_explosion(sr: int, params: dict[str, Any]) -> np.ndarray:
    """A big boom: low sine drop + long noise rumble."""
    duration = _num(params, "duration", 1.2)
    t = _t(sr, duration)
    rng = np.random.default_rng(_seed(params))
    noise = rng.normal(0.0, 0.5, len(t)).astype(np.float32)
    rumble = noise * np.exp(-t * 3.0)
    sub = np.sin(2 * np.pi * 45.0 * t) * np.exp(-t * 4.0)
    return np.asarray(rumble + sub * 0.9, dtype=np.float32)


def _gen_footstep(sr: int, params: dict[str, Any]) -> np.ndarray:
    """A single footstep: two short low thuds."""
    duration = _num(params, "duration", 0.2)
    t = _t(sr, duration)
    step = np.zeros_like(t)
    for start, freq in ((0.0, 110.0), (0.09, 80.0)):
        idx = int(start * sr)
        seg = np.arange(len(t) - idx, dtype=np.float32) / sr
        step[idx:] += np.sin(2 * np.pi * freq * seg) * np.exp(-seg * 40.0) * 0.6
    return np.asarray(step, dtype=np.float32)


def _gen_ambience(sr: int, params: dict[str, Any]) -> np.ndarray:
    """Room tone: steady filtered noise."""
    duration = _num(params, "duration", 3.0)
    rng = np.random.default_rng(_seed(params))
    noise = rng.normal(0.0, 0.12, int(sr * duration)).astype(np.float32)
    # Simple low-pass via moving average.
    window = max(1, int(sr * 0.002))
    kernel = np.ones(window) / window
    smooth = np.convolve(noise, kernel, mode="same")
    return np.asarray(smooth, dtype=np.float32)


def _gen_transition(sr: int, params: dict[str, Any]) -> np.ndarray:
    """A rising swell used to bridge scenes."""
    duration = _num(params, "duration", 0.8)
    t = _t(sr, duration)
    sweep = np.sin(2 * np.pi * (200.0 + 800.0 * t) * t)
    return np.asarray(_env_ar(sweep * 0.5, sr, 0.4, 0.4), dtype=np.float32)


def _gen_ui_click(sr: int, params: dict[str, Any]) -> np.ndarray:
    """A short UI click/ding."""
    duration = _num(params, "duration", 0.1)
    t = _t(sr, duration)
    tone = np.sin(2 * np.pi * 1200.0 * t) * np.exp(-t * 40.0)
    return np.asarray(tone * 0.5, dtype=np.float32)


def _num(params: dict[str, Any], key: str, default: float) -> float:
    try:
        return float(params.get(key, default))
    except (TypeError, ValueError) as exc:
        raise SfxError(f"'{key}' must be a number.") from exc


SFX: dict[str, Any] = {
    "whoosh": _gen_whoosh,
    "impact": _gen_impact,
    "explosion": _gen_explosion,
    "footstep": _gen_footstep,
    "ambience": _gen_ambience,
    "transition": _gen_transition,
    "ui_click": _gen_ui_click,
}

_SFX_DOCS: dict[str, str] = {
    "whoosh": "A rising-then-falling filtered noise sweep, for motion and transitions.",
    "impact": "A short percussive thump, for hits and impacts.",
    "explosion": "A big boom with a low sub-drop and long noise rumble.",
    "footstep": "A single footstep made of two short low thuds.",
    "ambience": "Steady room tone for filling quiet backgrounds.",
    "transition": "A rising swell used to bridge scenes.",
    "ui_click": "A short UI click/ding.",
}


def sfx_catalog() -> dict[str, Any]:
    """Every synthesised sound effect with a plain-language description."""
    return {
        "sfx": [
            {"name": name, "description": _SFX_DOCS.get(name, name)}
            for name in sorted(SFX)
        ]
    }


def synthesize_sfx(
    name: str, sr: int = 44100, params: dict[str, Any] | None = None
) -> np.ndarray:
    """Generate one sound effect as float32 mono PCM."""
    name = (name or "").lower()
    if name not in SFX:
        raise SfxError(f"Unknown SFX '{name}'. Known: {sorted(SFX)}")
    return np.asarray(SFX[name](sr, dict(params or {})), dtype=np.float32)
