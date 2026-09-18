"""Audio DSP effects — pure NumPy, offline, vision-free.

Each effect is a pure ``(samples, sample_rate, params) -> samples`` function
over float32 mono PCM. They implement the classic studio processors (EQ,
compressor, reverb, limiter, noise gate) and a simple pitch-shift voice changer
without any model, so a text-only agent can apply them to any audio and a
screen reader can explain them. Decoding/encoding to bytes is delegated to
:mod:`content_factory.voice_engine`, which shells out to ffmpeg.

:func:`audio_effect_catalog` returns plain-language descriptions of every effect
and its parameters — the accessibility seam for non-vision users and agents.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

__all__ = [
    "AUDIO_EFFECTS",
    "apply_audio_effect",
    "audio_effect_catalog",
    "audio_effect_names",
]


class AudioEffectError(ValueError):
    """Raised when an audio effect is malformed or cannot be applied."""


def _seed(params: dict[str, Any]) -> int:
    try:
        return int(params.get("seed", 0))
    except (TypeError, ValueError):
        return 0


def _num(params: dict[str, Any], key: str, default: float) -> float:
    try:
        return float(params.get(key, default))
    except (TypeError, ValueError) as exc:
        raise AudioEffectError(f"'{key}' must be a number.") from exc


def _clamp_db(value: float) -> float:
    return max(-60.0, min(0.0, value))


# --- Biquad peaking EQ -------------------------------------------------------


def _biquad_peaking(
    samples: np.ndarray, sr: int, freq: float, gain_db: float, q: float
) -> np.ndarray:
    """One peaking-EQ biquad (RBJ cookbook)."""
    if gain_db == 0:
        return samples
    a = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * math.pi * max(20.0, min(sr / 2.0 - 1.0, freq)) / sr
    alpha = math.sin(w0) / (2.0 * max(0.1, q))
    cos_w0 = math.cos(w0)
    b0 = 1.0 + alpha * a
    b1 = -2.0 * cos_w0
    b2 = 1.0 - alpha * a
    a0 = 1.0 + alpha / a
    a1 = -2.0 * cos_w0
    a2 = 1.0 - alpha / a
    b0, b1, b2 = b0 / a0, b1 / a0, b2 / a0
    a1, a2 = a1 / a0, a2 / a0
    out = np.empty_like(samples)
    x1 = x2 = y1 = y2 = 0.0
    for i, x in enumerate(samples):
        y = b0 * x + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        out[i] = y
        x2, x1 = x1, x
        y2, y1 = y1, y
    return out


def _fx_equalizer(samples: np.ndarray, sr: int, params: dict[str, Any]) -> np.ndarray:
    """Three-band peaking EQ: bass / mid / treble."""
    out = samples
    for freq, key in ((120.0, "bass_db"), (1000.0, "mid_db"), (6000.0, "treble_db")):
        out = _biquad_peaking(out, sr, freq, _num(params, key, 0.0), 0.7)
    return out


def _fx_compressor(samples: np.ndarray, sr: int, params: dict[str, Any]) -> np.ndarray:
    """Dynamic-range compressor: tames peaks above a threshold."""
    threshold = _clamp_db(_num(params, "threshold_db", -18.0))
    ratio = max(1.0, _num(params, "ratio", 3.0))
    makeup = _num(params, "makeup_db", 0.0)
    attack = max(0.001, _num(params, "attack_ms", 10.0))
    release = max(0.005, _num(params, "release_ms", 150.0))
    # Envelope follower on the absolute value (one-pole).
    alpha_a = math.exp(-1.0 / (sr * attack / 1000.0))
    alpha_r = math.exp(-1.0 / (sr * release / 1000.0))
    env = np.zeros_like(samples)
    level = 0.0
    for i, x in enumerate(np.abs(samples)):
        alpha = alpha_a if x > level else alpha_r
        level = alpha * level + (1.0 - alpha) * x
        env[i] = level
    eps = 1e-9
    db = 20.0 * np.log10(env + eps)
    over = np.maximum(db - threshold, 0.0)
    gain_db = -over * (1.0 - 1.0 / ratio) + makeup
    gain = 10.0 ** (gain_db / 20.0)
    return samples * gain


def _fx_limiter(samples: np.ndarray, sr: int, params: dict[str, Any]) -> np.ndarray:
    """Look-ahead-less brickwall-ish limiter (soft knee)."""
    ceiling = _clamp_db(_num(params, "ceiling_db", -1.0))
    ceiling_lin = 10.0 ** (ceiling / 20.0)
    peak = float(np.max(np.abs(samples))) or 1.0
    if peak <= ceiling_lin:
        return samples
    # Scale down smoothly so nothing exceeds the ceiling.
    scale = ceiling_lin / peak
    return np.asarray(samples * scale, dtype=np.float32)


def _fx_reverb(samples: np.ndarray, sr: int, params: dict[str, Any]) -> np.ndarray:
    """Schroeder reverb: parallel combs + series allpasses."""
    amount = max(0.0, min(1.0, _num(params, "amount", 0.3)))
    decay = max(0.1, min(0.9, _num(params, "decay", 0.5)))
    if amount <= 0:
        return samples
    comb_lengths = [1116, 1188, 1277, 1356, 1422, 1491]
    allpass_lengths = [225, 556, 441, 341]
    wet = np.zeros_like(samples)
    for length in comb_lengths:
        delay = max(1, round(length * sr / 44100))
        buf = np.zeros(delay)
        out = np.zeros_like(samples)
        for i, x in enumerate(samples):
            delayed = buf[i % delay]
            buf[i % delay] = x + delayed * decay
            out[i] = delayed
        wet += out
    wet /= len(comb_lengths)
    for length in allpass_lengths:
        delay = max(1, round(length * sr / 44100))
        buf = np.zeros(delay)
        out = np.zeros_like(wet)
        for i, x in enumerate(wet):
            delayed = buf[i % delay]
            buf[i % delay] = x + delayed * 0.5
            out[i] = -x + delayed
        wet = out
    return samples * (1.0 - amount) + wet * amount


def _fx_voice_changer(
    samples: np.ndarray, sr: int, params: dict[str, Any]
) -> np.ndarray:
    """Pitch shift by resampling (chipmunk up, monster down)."""
    semitones = _num(params, "semitones", 0.0)
    if semitones == 0:
        return samples
    factor = 2.0 ** (semitones / 12.0)
    n = max(1, int(len(samples) / factor))
    xp = np.linspace(0.0, len(samples) - 1.0, n)
    return np.asarray(np.interp(xp, np.arange(len(samples)), samples), dtype=np.float32)


def _fx_noise_gate(samples: np.ndarray, sr: int, params: dict[str, Any]) -> np.ndarray:
    """Gate: silence audio below a threshold, with a soft ramp."""
    threshold = _clamp_db(_num(params, "threshold_db", -40.0))
    attack = max(0.001, _num(params, "attack_ms", 5.0))
    release = max(0.005, _num(params, "release_ms", 100.0))
    thr = 10.0 ** (threshold / 20.0)
    alpha_a = math.exp(-1.0 / (sr * attack / 1000.0))
    alpha_r = math.exp(-1.0 / (sr * release / 1000.0))
    gate = np.zeros_like(samples)
    level = 0.0
    for i, x in enumerate(np.abs(samples)):
        alpha = alpha_a if x > level else alpha_r
        level = alpha * level + (1.0 - alpha) * x
        gate[i] = 1.0 if level >= thr else 0.0
    return samples * gate


AUDIO_EFFECTS: dict[str, Any] = {
    "equalizer": _fx_equalizer,
    "compressor": _fx_compressor,
    "limiter": _fx_limiter,
    "reverb": _fx_reverb,
    "voice_changer": _fx_voice_changer,
    "noise_gate": _fx_noise_gate,
}


def audio_effect_names() -> list[str]:
    """Names of every available audio effect."""
    return sorted(AUDIO_EFFECTS)


def apply_audio_effect(
    samples: np.ndarray, sr: int, name: str, params: dict[str, Any] | None = None
) -> np.ndarray:
    """Apply one named effect to float32 mono PCM."""
    name = (name or "").lower()
    if name not in AUDIO_EFFECTS:
        raise AudioEffectError(
            f"Unknown effect '{name}'. Known: {sorted(AUDIO_EFFECTS)}"
        )
    arr = np.asarray(samples, dtype=np.float32)
    if arr.ndim != 1:
        raise AudioEffectError("Audio effects operate on mono PCM (1-D array).")
    result = AUDIO_EFFECTS[name](arr, int(sr), dict(params or {}))
    return np.asarray(result, dtype=np.float32)


#: Plain-language docs for every effect, for the accessibility layer.
_AUDIO_DOCS: dict[str, dict[str, Any]] = {
    "equalizer": {
        "description": "Three-band equalizer: boost or cut bass, mid and treble "
        "to shape the tone.",
        "params": {
            "bass_db": "Gain at ~120 Hz (dB).",
            "mid_db": "Gain at ~1 kHz (dB).",
            "treble_db": "Gain at ~6 kHz (dB).",
        },
    },
    "compressor": {
        "description": "Compressor: tames peaks above a threshold so the level "
        "stays even, with makeup gain.",
        "params": {
            "threshold_db": "Level above which compression kicks in.",
            "ratio": "How strongly peaks are reduced (>=1).",
            "makeup_db": "Make-up gain to restore loudness.",
            "attack_ms": "Attack time in ms.",
            "release_ms": "Release time in ms.",
        },
    },
    "limiter": {
        "description": "Limiter: prevents any sample from exceeding a ceiling, "
        "stopping clipping.",
        "params": {"ceiling_db": "Maximum output level (dB)."},
    },
    "reverb": {
        "description": "Schroeder reverb: adds a spacious room ambience.",
        "params": {"amount": "0..1 wet/dry mix.", "decay": "0.1..0.9 tail length."},
    },
    "voice_changer": {
        "description": "Voice changer: shifts pitch by semitones (positive = "
        "chipmunk, negative = deep monster).",
        "params": {"semitones": "Pitch shift in semitones."},
    },
    "noise_gate": {
        "description": "Noise gate: silences audio below a threshold to remove "
        "breaths and hiss.",
        "params": {
            "threshold_db": "Level below which audio is silenced.",
            "attack_ms": "How fast the gate opens.",
            "release_ms": "How fast the gate closes.",
        },
    },
}


def audio_effect_catalog() -> dict[str, Any]:
    """Every audio effect with a plain-language description and parameters."""
    return {
        "effects": [
            {
                "name": name,
                **(_AUDIO_DOCS.get(name, {"description": name, "params": {}})),
            }
            for name in sorted(AUDIO_EFFECTS)
        ]
    }
