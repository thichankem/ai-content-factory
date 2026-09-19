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


# --- Biquad filters ----------------------------------------------------------


def _biquad(
    samples: np.ndarray, sr: int, coeffs: tuple[float, float, float, float, float]
) -> np.ndarray:
    """Apply a biquad from its (b0,b1,b2,a1,a2) coefficients (a0 normalised to 1)."""
    b0, b1, b2, a1, a2 = coeffs
    out = np.empty_like(samples)
    x1 = x2 = y1 = y2 = 0.0
    for i, x in enumerate(samples):
        y = b0 * x + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        out[i] = y
        x2, x1 = x1, x
        y2, y1 = y1, y
    return out


def _rbj_coeffs(
    freq: float, sr: int, kind: str, q: float, gain_db: float = 0.0
) -> tuple[float, float, float, float, float]:
    """RBJ cookbook biquad coefficients for a filter type."""
    w0 = 2.0 * math.pi * max(10.0, min(sr / 2.0 - 1.0, freq)) / sr
    cw = math.cos(w0)
    sw = math.sin(w0)
    alpha = sw / (2.0 * max(0.1, q))
    a = 10.0 ** (gain_db / 40.0)
    if kind == "highpass":
        # RBJ high-pass: the numerator is built from cos(w0), not from the
        # shelf gain factor. Using ``a`` here (and dropping the z^-2 term)
        # turned this into a bare differentiator whose response rose to ~57x
        # near the cutoff instead of rolling off below it.
        b0, b1, b2 = (1 + cw) / 2, -(1 + cw), (1 + cw) / 2
        a0, a1, a2 = 1 + alpha, -2 * cw, 1 - alpha
    elif kind == "lowpass":
        b0, b1, b2 = (1 - cw) / 2, 1 - cw, (1 - cw) / 2
        a0, a1, a2 = 1 + alpha, -2 * cw, 1 - alpha
    elif kind == "bandpass":
        b0, b1, b2 = alpha, 0.0, -alpha
        a0, a1, a2 = 1 + alpha, -2 * cw, 1 - alpha
    elif kind == "notch":
        b0, b1, b2 = 1.0, -2 * cw, 1.0
        a0, a1, a2 = 1 + alpha, -2 * cw, 1 - alpha
    elif kind == "lowshelf":
        beta = math.sqrt(a) * alpha
        b0 = a * ((a + 1) - (a - 1) * cw + beta)
        b1 = 2 * a * ((a - 1) - (a + 1) * cw)
        b2 = a * ((a + 1) - (a - 1) * cw - beta)
        a0 = (a + 1) + (a - 1) * cw + beta
        a1 = -2 * ((a - 1) + (a + 1) * cw)
        a2 = (a + 1) + (a - 1) * cw - beta
    else:  # highshelf
        beta = math.sqrt(a) * alpha
        b0 = a * ((a + 1) + (a - 1) * cw + beta)
        b1 = -2 * a * ((a - 1) + (a + 1) * cw)
        b2 = a * ((a + 1) + (a - 1) * cw - beta)
        a0 = (a + 1) - (a - 1) * cw + beta
        a1 = 2 * ((a - 1) - (a + 1) * cw)
        a2 = (a + 1) - (a - 1) * cw - beta
    return (b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0)


def _fx_highpass(samples: np.ndarray, sr: int, params: dict[str, Any]) -> np.ndarray:
    return _biquad(
        samples, sr, _rbj_coeffs(_num(params, "freq", 80.0), sr, "highpass", 0.707)
    )


def _fx_lowpass(samples: np.ndarray, sr: int, params: dict[str, Any]) -> np.ndarray:
    return _biquad(
        samples, sr, _rbj_coeffs(_num(params, "freq", 8000.0), sr, "lowpass", 0.707)
    )


def _fx_bandpass(samples: np.ndarray, sr: int, params: dict[str, Any]) -> np.ndarray:
    return _biquad(
        samples,
        sr,
        _rbj_coeffs(
            _num(params, "freq", 1000.0), sr, "bandpass", _num(params, "q", 1.0)
        ),
    )


def _fx_notch(samples: np.ndarray, sr: int, params: dict[str, Any]) -> np.ndarray:
    return _biquad(
        samples,
        sr,
        _rbj_coeffs(_num(params, "freq", 50.0), sr, "notch", _num(params, "q", 10.0)),
    )


def _fx_lowshelf(samples: np.ndarray, sr: int, params: dict[str, Any]) -> np.ndarray:
    return _biquad(
        samples,
        sr,
        _rbj_coeffs(
            _num(params, "freq", 200.0),
            sr,
            "lowshelf",
            0.707,
            _num(params, "gain_db", 0.0),
        ),
    )


def _fx_highshelf(samples: np.ndarray, sr: int, params: dict[str, Any]) -> np.ndarray:
    return _biquad(
        samples,
        sr,
        _rbj_coeffs(
            _num(params, "freq", 4000.0),
            sr,
            "highshelf",
            0.707,
            _num(params, "gain_db", 0.0),
        ),
    )


# --- Additional dynamics -----------------------------------------------------


def _fx_expander(samples: np.ndarray, sr: int, params: dict[str, Any]) -> np.ndarray:
    """Expander: attenuates signals below the threshold (opposite of a gate)."""
    threshold = _clamp_db(_num(params, "threshold_db", -30.0))
    ratio = max(1.0, _num(params, "ratio", 2.0))
    attack = max(0.001, _num(params, "attack_ms", 10.0))
    release = max(0.005, _num(params, "release_ms", 120.0))
    alpha_a = math.exp(-1.0 / (sr * attack / 1000.0))
    alpha_r = math.exp(-1.0 / (sr * release / 1000.0))
    env = np.zeros_like(samples)
    level = 0.0
    for i, x in enumerate(np.abs(samples)):
        alpha = alpha_a if x > level else alpha_r
        level = alpha * level + (1.0 - alpha) * x
        env[i] = level
    db = 20.0 * np.log10(env + 1e-9)
    below = np.maximum(threshold - db, 0.0)
    gain_db = below * (ratio - 1.0)
    return samples * (10.0 ** (-gain_db / 20.0))


def _fx_de_esser(samples: np.ndarray, sr: int, params: dict[str, Any]) -> np.ndarray:
    """De-esser: attenuates harsh sibilance around 6 kHz."""
    freq = _num(params, "freq", 6000.0)
    amount = _clamp_db(_num(params, "amount_db", -8.0))
    high = _biquad(samples, sr, _rbj_coeffs(freq, sr, "bandpass", 2.0))
    # Envelope of the sibilance band drives a gain reduction on the full signal.
    env = np.abs(high)
    window = max(1, int(sr * 0.003))
    smooth = np.convolve(env, np.ones(window) / window, mode="same")
    peak = float(np.max(smooth)) or 1.0
    gain = 1.0 + (10.0 ** (amount / 20.0) - 1.0) * (smooth / peak)
    return np.asarray(samples * gain, dtype=np.float32)


def _fx_clipper(samples: np.ndarray, sr: int, params: dict[str, Any]) -> np.ndarray:
    """Soft clipper: rounds peaks for a louder, denser sound."""
    drive = max(1.0, _num(params, "drive", 1.0))
    return np.tanh(samples * drive)


def _fx_saturation(samples: np.ndarray, sr: int, params: dict[str, Any]) -> np.ndarray:
    """Harmonic saturation (soft tanh drive)."""
    amount = max(0.0, _num(params, "amount", 1.0))
    return np.asarray(np.tanh(samples * (1.0 + amount)), dtype=np.float32)


# --- Creative effects --------------------------------------------------------


def _fx_delay(samples: np.ndarray, sr: int, params: dict[str, Any]) -> np.ndarray:
    """Single delay tap."""
    delay_ms = max(1.0, _num(params, "delay_ms", 250.0))
    feedback = max(0.0, min(0.95, _num(params, "feedback", 0.3)))
    mix = max(0.0, min(1.0, _num(params, "mix", 0.3)))
    taps = max(1, round(sr * delay_ms / 1000.0))
    out = np.zeros_like(samples)
    buf = np.zeros(taps)
    for i, x in enumerate(samples):
        delayed = buf[i % taps]
        buf[i % taps] = x + delayed * feedback
        out[i] = delayed
    return samples * (1.0 - mix) + out * mix


def _fx_echo(samples: np.ndarray, sr: int, params: dict[str, Any]) -> np.ndarray:
    """Echo: a louder, longer feedback delay."""
    return _fx_delay(
        samples,
        sr,
        {
            "delay_ms": _num(params, "delay_ms", 300.0),
            "feedback": _num(params, "feedback", 0.6),
            "mix": _num(params, "mix", 0.4),
        },
    )


def _fx_chorus(samples: np.ndarray, sr: int, params: dict[str, Any]) -> np.ndarray:
    """Chorus: a modulated short delay layered over the dry signal."""
    depth_ms = max(0.5, _num(params, "depth_ms", 4.0))
    rate = max(0.1, _num(params, "rate_hz", 1.5))
    mix = max(0.0, min(1.0, _num(params, "mix", 0.4)))
    base = max(1, round(sr * 0.015))
    depth = max(1, round(sr * depth_ms / 1000.0))
    out = np.zeros_like(samples)
    buf = np.zeros(base + depth + 2)
    for i, x in enumerate(samples):
        mod = depth * (0.5 + 0.5 * math.sin(2 * math.pi * rate * i / sr))
        idx = (i - int(mod)) % len(buf)
        out[i] = buf[idx]
        buf[i % len(buf)] = x
    return samples * (1.0 - mix) + out * mix


def _fx_flanger(samples: np.ndarray, sr: int, params: dict[str, Any]) -> np.ndarray:
    """Flanger: a sweeping comb-filter effect."""
    rate = max(0.1, _num(params, "rate_hz", 0.5))
    depth_ms = max(0.5, _num(params, "depth_ms", 3.0))
    mix = max(0.0, min(1.0, _num(params, "mix", 0.5)))
    base = max(1, round(sr * 0.004))
    depth = max(1, round(sr * depth_ms / 1000.0))
    out = np.zeros_like(samples)
    buf = np.zeros(base + depth + 2)
    for i, x in enumerate(samples):
        mod = depth * (0.5 + 0.5 * math.sin(2 * math.pi * rate * i / sr))
        idx = (i - int(mod)) % len(buf)
        out[i] = x + buf[idx]
        buf[i % len(buf)] = x
    return samples * (1.0 - mix) + out * mix


def _fx_phaser(samples: np.ndarray, sr: int, params: dict[str, Any]) -> np.ndarray:
    """Phaser: swept all-pass notches."""
    rate = max(0.1, _num(params, "rate_hz", 0.7))
    depth = max(0.0, min(1.0, _num(params, "depth", 0.7)))
    mix = max(0.0, min(1.0, _num(params, "mix", 0.5)))
    out = np.zeros_like(samples)
    phase = 0.0
    for i, x in enumerate(samples):
        lfo = 0.5 + 0.5 * math.sin(2 * math.pi * rate * i / sr)
        coeff = 0.4 + 0.5 * depth * lfo
        phase = x * (1.0 - coeff) + phase * coeff
        out[i] = x * (1.0 - mix) + phase * mix
    return out


def _fx_distortion(samples: np.ndarray, sr: int, params: dict[str, Any]) -> np.ndarray:
    """Hard distortion: waveshaper with adjustable drive."""
    drive = max(1.0, _num(params, "drive", 4.0))
    return np.clip(np.tanh(samples * drive) * (1.0 + 0.3 * drive), -1.0, 1.0)


def _fx_bitcrusher(samples: np.ndarray, sr: int, params: dict[str, Any]) -> np.ndarray:
    """Bitcrusher: reduces bit depth and sample rate for a lo-fi crunch."""
    bits = max(1, int(_num(params, "bits", 4.0)))
    steps = 2.0**bits
    crushed = np.round(samples * steps) / steps
    # Sample-rate reduction via step-hold.
    hold = max(1, int(_num(params, "downsample", 4.0)))
    return np.repeat(crushed[::hold], hold)[: len(samples)]


def _fx_tremolo(samples: np.ndarray, sr: int, params: dict[str, Any]) -> np.ndarray:
    """Tremolo: amplitude modulation."""
    rate = max(0.1, _num(params, "rate_hz", 5.0))
    depth = max(0.0, min(1.0, _num(params, "depth", 0.8)))
    t = np.arange(len(samples)) / sr
    mod = 1.0 - depth * (0.5 + 0.5 * np.sin(2 * np.pi * rate * t))
    return samples * mod


def _fx_vibrato(samples: np.ndarray, sr: int, params: dict[str, Any]) -> np.ndarray:
    """Vibrato: pitch modulation via a varying delay."""
    rate = max(0.1, _num(params, "rate_hz", 5.0))
    depth_ms = max(0.5, _num(params, "depth_ms", 5.0))
    depth = max(1, round(sr * depth_ms / 1000.0))
    base = max(1, round(sr * 0.012))
    out = np.zeros_like(samples)
    buf = np.zeros(base + depth + 2)
    for i, x in enumerate(samples):
        mod = depth * (0.5 + 0.5 * math.sin(2 * math.pi * rate * i / sr))
        idx = (i - int(mod)) % len(buf)
        out[i] = buf[idx]
        buf[i % len(buf)] = x
    return out


def _fx_ring_modulation(
    samples: np.ndarray, sr: int, params: dict[str, Any]
) -> np.ndarray:
    """Ring modulation: multiply by a carrier sine for metallic timbres."""
    freq = max(20.0, _num(params, "freq", 440.0))
    t = np.arange(len(samples)) / sr
    carrier = np.sin(2 * np.pi * freq * t)
    return np.asarray(samples * carrier, dtype=np.float32)


def _fx_telephone(samples: np.ndarray, sr: int, params: dict[str, Any]) -> np.ndarray:
    """Telephone: band-limited, lo-fi voice."""
    band = _biquad(samples, sr, _rbj_coeffs(300.0, sr, "highpass", 0.707))
    band = _biquad(band, sr, _rbj_coeffs(3400.0, sr, "lowpass", 0.707))
    return np.clip(band * 3.0, -1.0, 1.0)


def _fx_radio(samples: np.ndarray, sr: int, params: dict[str, Any]) -> np.ndarray:
    """Radio: mid-band voice with slight distortion and noise."""
    band = _biquad(samples, sr, _rbj_coeffs(200.0, sr, "highpass", 0.707))
    band = _biquad(band, sr, _rbj_coeffs(4000.0, sr, "lowpass", 0.707))
    shaped = np.tanh(band * 2.0)
    rng = np.random.default_rng(_seed(params))
    noise = rng.normal(0.0, 0.006, len(samples))
    return np.clip(shaped * 2.0 + noise, -1.0, 1.0)


def _fx_megaphone(samples: np.ndarray, sr: int, params: dict[str, Any]) -> np.ndarray:
    """Megaphone: compressed, distorted, clipped voice."""
    band = _biquad(samples, sr, _rbj_coeffs(400.0, sr, "highpass", 0.707))
    band = _biquad(band, sr, _rbj_coeffs(3000.0, sr, "lowpass", 0.707))
    return np.clip(np.tanh(band * 4.0) * 1.2, -1.0, 1.0)


def _fx_underwater(samples: np.ndarray, sr: int, params: dict[str, Any]) -> np.ndarray:
    """Underwater: muffled, low-passed with a slow wobble."""
    low = _biquad(samples, sr, _rbj_coeffs(600.0, sr, "lowpass", 0.707))
    rate = max(0.1, _num(params, "rate_hz", 0.8))
    t = np.arange(len(samples)) / sr
    wobble = 0.85 + 0.15 * np.sin(2 * np.pi * rate * t)
    return low * wobble


def _fx_robot(samples: np.ndarray, sr: int, params: dict[str, Any]) -> np.ndarray:
    """Robot: ring-modulated, formant-y voice."""
    t = np.arange(len(samples)) / sr
    carrier = np.sin(2 * np.pi * 80.0 * t)
    clipped = np.clip(samples * (0.6 + 0.4 * carrier), -1.0, 1.0)
    return np.asarray(clipped, dtype=np.float32)


def _fx_reverse(samples: np.ndarray, sr: int, params: dict[str, Any]) -> np.ndarray:
    """Reverse: plays the audio backwards."""
    return samples[::-1].copy()


AUDIO_EFFECTS: dict[str, Any] = {
    "equalizer": _fx_equalizer,
    "compressor": _fx_compressor,
    "limiter": _fx_limiter,
    "reverb": _fx_reverb,
    "voice_changer": _fx_voice_changer,
    "noise_gate": _fx_noise_gate,
    # filters
    "highpass": _fx_highpass,
    "lowpass": _fx_lowpass,
    "bandpass": _fx_bandpass,
    "notch": _fx_notch,
    "lowshelf": _fx_lowshelf,
    "highshelf": _fx_highshelf,
    # dynamics
    "expander": _fx_expander,
    "de_esser": _fx_de_esser,
    "clipper": _fx_clipper,
    "saturation": _fx_saturation,
    # creative
    "delay": _fx_delay,
    "echo": _fx_echo,
    "chorus": _fx_chorus,
    "flanger": _fx_flanger,
    "phaser": _fx_phaser,
    "distortion": _fx_distortion,
    "bitcrusher": _fx_bitcrusher,
    "tremolo": _fx_tremolo,
    "vibrato": _fx_vibrato,
    "ring_modulation": _fx_ring_modulation,
    "telephone": _fx_telephone,
    "radio": _fx_radio,
    "megaphone": _fx_megaphone,
    "underwater": _fx_underwater,
    "robot": _fx_robot,
    "reverse": _fx_reverse,
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
    # filters
    "highpass": {
        "description": "High-pass filter: removes low rumble below a frequency.",
        "params": {"freq": "Cutoff frequency in Hz."},
    },
    "lowpass": {
        "description": "Low-pass filter: removes harsh highs above a frequency.",
        "params": {"freq": "Cutoff frequency in Hz."},
    },
    "bandpass": {
        "description": "Band-pass filter: keeps only a band of frequencies.",
        "params": {"freq": "Centre frequency.", "q": "Bandwidth (higher = narrower)."},
    },
    "notch": {
        "description": "Notch filter: removes a single frequency (e.g. mains hum).",
        "params": {"freq": "Frequency to remove.", "q": "Bandwidth."},
    },
    "lowshelf": {
        "description": "Low shelf: boosts or cuts all frequencies below a point.",
        "params": {"freq": "Shelf frequency.", "gain_db": "Gain in dB."},
    },
    "highshelf": {
        "description": "High shelf: boosts or cuts all frequencies above a point.",
        "params": {"freq": "Shelf frequency.", "gain_db": "Gain in dB."},
    },
    # dynamics
    "expander": {
        "description": "Expander: attenuates quiet signals below a threshold, "
        "widening the dynamic range.",
        "params": {
            "threshold_db": "Level below which attenuation starts.",
            "ratio": "How much to attenuate.",
        },
    },
    "de_esser": {
        "description": "De-esser: tames harsh sibilance around 6 kHz.",
        "params": {"freq": "Sibilance band centre.", "amount_db": "How much to cut."},
    },
    "clipper": {
        "description": "Clipper: rounds peaks for a louder, denser sound.",
        "params": {"drive": "Amount of drive (>=1)."},
    },
    "saturation": {
        "description": "Saturation: adds harmonic warmth via soft drive.",
        "params": {"amount": "How much saturation (>=0)."},
    },
    # creative
    "delay": {
        "description": "Delay: a single echo tap with feedback.",
        "params": {
            "delay_ms": "Delay time in ms.",
            "feedback": "How much repeats.",
            "mix": "Wet/dry mix.",
        },
    },
    "echo": {
        "description": "Echo: a louder, longer feedback delay.",
        "params": {
            "delay_ms": "Delay time.",
            "feedback": "Feedback amount.",
            "mix": "Wet/dry mix.",
        },
    },
    "chorus": {
        "description": "Chorus: a modulated short delay layered over the dry signal.",
        "params": {
            "depth_ms": "Modulation depth.",
            "rate_hz": "Modulation rate.",
            "mix": "Wet/dry mix.",
        },
    },
    "flanger": {
        "description": "Flanger: a sweeping comb-filter jet-like effect.",
        "params": {
            "rate_hz": "Sweep rate.",
            "depth_ms": "Depth.",
            "mix": "Wet/dry mix.",
        },
    },
    "phaser": {
        "description": "Phaser: swept all-pass notches, a swirling effect.",
        "params": {
            "rate_hz": "Sweep rate.",
            "depth": "Depth 0..1.",
            "mix": "Wet/dry mix.",
        },
    },
    "distortion": {
        "description": "Distortion: hard waveshaper for aggressive grit.",
        "params": {"drive": "Amount of drive (>=1)."},
    },
    "bitcrusher": {
        "description": "Bitcrusher: reduces bit depth and sample rate for a "
        "lo-fi crunch.",
        "params": {"bits": "Bit depth (>=1).", "downsample": "Sample-rate divisor."},
    },
    "tremolo": {
        "description": "Tremolo: rhythmic amplitude modulation.",
        "params": {"rate_hz": "Modulation rate.", "depth": "Depth 0..1."},
    },
    "vibrato": {
        "description": "Vibrato: pitch modulation via a varying delay.",
        "params": {"rate_hz": "Modulation rate.", "depth_ms": "Pitch depth."},
    },
    "ring_modulation": {
        "description": "Ring modulation: multiplies by a carrier sine for "
        "metallic, sci-fi timbres.",
        "params": {"freq": "Carrier frequency in Hz."},
    },
    "telephone": {
        "description": "Telephone: band-limited, lo-fi voice.",
        "params": {},
    },
    "radio": {
        "description": "Radio: mid-band voice with slight distortion and noise.",
        "params": {"seed": "Random seed for the noise."},
    },
    "megaphone": {
        "description": "Megaphone: compressed, distorted, clipped voice.",
        "params": {},
    },
    "underwater": {
        "description": "Underwater: muffled, low-passed with a slow wobble.",
        "params": {"rate_hz": "Wobble rate."},
    },
    "robot": {
        "description": "Robot: ring-modulated, formant-y robotic voice.",
        "params": {},
    },
    "reverse": {
        "description": "Reverse: plays the audio backwards.",
        "params": {},
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
