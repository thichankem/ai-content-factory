"""Voice engine — Adobe Audition/Podcast-style audio post-production.

Works on real PCM audio with numpy and encodes/decodes via ffmpeg. Provides
the classic speech chain: normalize → high-pass → noise-gate → de-ess (rough)
→ EQ → compressor → loudness target, plus creative effects (reverb send,
telephone EQ), speed/pitch changes, fades, and ducking of a music bed under
the voice. Pure functions over bytes so it is testable and callable from the
agent tools registry.
"""

from __future__ import annotations

import math
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

__all__ = [
    "KNOWN_CHAIN_STEPS",
    "VoiceChain",
    "VoiceError",
    "duck_music",
    "process_voice",
]

_SR = 44100
_CHANNELS = 2


class VoiceError(ValueError):
    """Raised when a voice-processing step is malformed or fails."""


def _ffmpeg() -> str:
    import shutil

    binary = shutil.which("ffmpeg")
    if binary is None:
        raise VoiceError("ffmpeg is required for audio processing.")
    return binary


def decode_to_pcm(data: bytes) -> tuple[np.ndarray, int]:
    """Decode any audio bytes to float32 mono PCM at 44.1 kHz."""
    if not data:
        raise VoiceError("Empty audio payload.")
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as tmp:
        tmp.write(data)
        src = tmp.name
    try:
        cmd = [
            _ffmpeg(),
            "-v",
            "error",
            "-i",
            src,
            "-f",
            "f32le",
            "-acodec",
            "pcm_f32le",
            "-ac",
            "1",
            "-ar",
            str(_SR),
            "-",
        ]
        raw = subprocess.run(cmd, capture_output=True, check=True, timeout=120).stdout
    except subprocess.CalledProcessError as exc:
        raise VoiceError(f"Cannot decode audio: {exc.stderr[-200:]!r}") from exc
    finally:
        Path(src).unlink(missing_ok=True)
    samples = np.frombuffer(raw, dtype=np.float32).copy()
    if samples.size == 0:
        raise VoiceError("Decoded audio is empty.")
    return samples, _SR


def encode_pcm(samples: np.ndarray, sr: int = _SR, fmt: str = "mp3") -> bytes:
    """Encode float32 mono PCM back to mp3/wav bytes."""
    fmt = fmt.lower()
    if fmt not in ("mp3", "wav"):
        raise VoiceError(f"Unsupported audio export format '{fmt}'. Use mp3/wav.")
    with tempfile.NamedTemporaryFile(suffix=f".{fmt}", delete=False) as tmp:
        dst = tmp.name
    args = ["-f", "f32le", "-acodec", "pcm_f32le", "-ac", "1", "-ar", str(sr)]
    out_args = ["-b:a", "192k"] if fmt == "mp3" else []
    try:
        subprocess.run(
            [_ffmpeg(), "-v", "error", *args, "-i", "-", "-y", *out_args, dst],
            input=samples.astype(np.float32).tobytes(),
            capture_output=True,
            check=True,
            timeout=120,
        )
        return Path(dst).read_bytes()
    except subprocess.CalledProcessError as exc:
        raise VoiceError(f"Cannot encode audio: {exc.stderr[-200:]!r}") from exc
    finally:
        Path(dst).unlink(missing_ok=True)


# --- DSP steps ----------------------------------------------------------------


def _moving_average(size: int) -> np.ndarray:
    return np.ones(size) / size


def _highpass(samples: np.ndarray, freq: float, sr: int) -> np.ndarray:
    """One-pole high-pass: removes rumble below ``freq`` Hz."""
    rc = 1.0 / (2.0 * math.pi * max(10.0, freq))
    dt = 1.0 / sr
    alpha = rc / (rc + dt)
    # Vectorized first-difference approximation is fine for speech rumble.
    diff = np.diff(samples, prepend=samples[0])
    return (alpha * diff).astype(np.float32)


def _lowpass(samples: np.ndarray, freq: float, sr: int) -> np.ndarray:
    """Simple moving-average low-pass sized to the cutoff frequency."""
    size = max(1, int(sr / max(100.0, freq)))
    kernel = _moving_average(size)
    return np.convolve(samples, kernel, mode="same").astype(np.float32)


def _noise_gate(samples: np.ndarray, threshold_db: float) -> np.ndarray:
    """Gate: zero out samples below the threshold relative to peak."""
    peak = np.max(np.abs(samples)) or 1.0
    threshold = peak * (10 ** (threshold_db / 20.0))
    quiet = np.abs(samples) < threshold
    # Smooth attack/release with a short moving mask.
    mask = (~quiet).astype(np.float32)
    smooth = np.convolve(mask, _moving_average(256), mode="same")
    return (samples * smooth).astype(np.float32)


def _de_ess(samples: np.ndarray, sr: int, strength: float) -> np.ndarray:
    """Rough de-esser: attenuate 5–8 kHz band energy where it spikes."""
    if strength <= 0:
        return samples
    hi = samples - _lowpass(samples, 5000.0, sr)
    hi_energy = np.abs(hi)
    threshold = np.percentile(hi_energy, 95) * (1.0 - strength)
    sibilant = (hi_energy > threshold).astype(np.float32)
    mask = np.convolve(sibilant, _moving_average(128), mode="same")
    return (samples - hi * mask * strength).astype(np.float32)  # type: ignore[no-any-return]


def _compress(samples: np.ndarray, ratio: float, threshold_db: float) -> np.ndarray:
    """Downward compressor over the absolute envelope."""
    peak = np.max(np.abs(samples)) or 1.0
    threshold = peak * (10 ** (threshold_db / 20.0))
    env = np.abs(samples)
    env = np.convolve(env, _moving_average(512), mode="same")
    over = env > threshold
    gain = np.ones_like(samples)
    gain[over] = (threshold / env[over]) ** (1.0 - 1.0 / max(1.0, ratio))
    return (samples * gain).astype(np.float32)


def _eq_bands(
    samples: np.ndarray, sr: int, low: float, mid: float, high: float
) -> np.ndarray:
    """3-band EQ: low shelf, mid bell, high shelf via crossover splits."""
    lo = _lowpass(samples, 250.0, sr)
    mid_band = _lowpass(samples, 4000.0, sr) - lo
    hi = samples - _lowpass(samples, 4000.0, sr)
    out = lo * low + mid_band * mid + hi * high
    return out.astype(np.float32)  # type: ignore[no-any-return]


def _normalize_loudness(samples: np.ndarray, target_lufs: float) -> np.ndarray:
    """Rough loudness normalize via RMS (EBU R128 uses gated LUFS; close enough)."""
    rms = math.sqrt(float(np.mean(samples**2))) or 1e-9
    current = 20.0 * math.log10(rms)
    gain = 10 ** ((target_lufs - current) / 20.0)
    gain = min(gain, 20.0)
    out = samples * gain
    peak = np.max(np.abs(out)) or 1.0
    if peak > 0.99:
        out = out * (0.99 / peak)
    return out.astype(np.float32)


def _reverb_send(samples: np.ndarray, sr: int, mix: float) -> np.ndarray:
    """Cheap multi-tap reverb (room feel)."""
    if mix <= 0:
        return samples
    taps = [(0.011, 0.5), (0.019, 0.4), (0.029, 0.3), (0.041, 0.25)]
    wet = np.zeros_like(samples)
    for delay_s, gain in taps:
        d = int(delay_s * sr)
        wet[d:] += samples[:-d] * gain if d < len(samples) else 0.0
    out = samples * (1.0 - mix) + wet * mix
    return out.astype(np.float32)


def _telephone(samples: np.ndarray, sr: int) -> np.ndarray:
    band = _lowpass(samples, 3400.0, sr) - _lowpass(samples, 300.0, sr)
    return (band * 1.4).astype(np.float32)  # type: ignore[no-any-return]


def _fade(samples: np.ndarray, sr: int, fade_in: float, fade_out: float) -> np.ndarray:
    out = samples.copy()
    n_in = int(min(fade_in, len(samples) / sr) * sr)
    n_out = int(min(fade_out, len(samples) / sr) * sr)
    if n_in > 0:
        ramp = np.linspace(0.0, 1.0, n_in, dtype=np.float32)
        out[:n_in] *= ramp
    if n_out > 0:
        ramp = np.linspace(1.0, 0.0, n_out, dtype=np.float32)
        out[-n_out:] *= ramp
    return out


# --- Chain configuration --------------------------------------------------------


@dataclass
class VoiceChain:
    """Declarative description of the processing chain (agent-editable)."""

    highpass_hz: float = 80.0
    gate_db: float | None = -42.0
    de_ess: float = 0.4
    eq_low: float = 1.0
    eq_mid: float = 1.1
    eq_high: float = 1.25
    compressor_ratio: float = 3.0
    compressor_threshold_db: float = -18.0
    target_lufs: float = -16.0
    reverb_mix: float = 0.0
    telephone: bool = False
    fade_in: float = 0.02
    fade_out: float = 0.15
    extras: dict[str, Any] = field(default_factory=dict)


def _from_params(params: dict[str, Any]) -> VoiceChain:
    chain = VoiceChain()
    mapping = {
        "highpass_hz": float,
        "gate_db": float,
        "de_ess": float,
        "eq_low": float,
        "eq_mid": float,
        "eq_high": float,
        "compressor_ratio": float,
        "compressor_threshold_db": float,
        "target_lufs": float,
        "reverb_mix": float,
        "fade_in": float,
        "fade_out": float,
    }
    for key, caster in mapping.items():
        if key in params and params[key] is not None:
            setattr(chain, key, caster(params[key]))
    # ``gate_db: None`` explicitly disables the noise gate (vs. omitting the
    # key, which keeps the default threshold).
    if "gate_db" in params:
        chain.gate_db = None if params["gate_db"] is None else float(params["gate_db"])
    if "telephone" in params:
        chain.telephone = bool(params["telephone"])
    return chain


#: Exposed for the tools manifest / agent discoverability.
KNOWN_CHAIN_STEPS = [
    "highpass_hz",
    "gate_db",
    "de_ess",
    "eq_low",
    "eq_mid",
    "eq_high",
    "compressor_ratio",
    "compressor_threshold_db",
    "target_lufs",
    "reverb_mix",
    "telephone",
    "fade_in",
    "fade_out",
]

#: Presets (radio/podcast/soft) an agent can request by name.
CHAIN_PRESETS: dict[str, dict[str, Any]] = {
    "podcast": {"target_lufs": -16.0, "eq_high": 1.3, "compressor_ratio": 3.0},
    "voiceover": {"target_lufs": -14.0, "eq_high": 1.35, "de_ess": 0.5},
    "soft": {"compressor_ratio": 2.0, "eq_high": 1.1, "gate_db": -50.0},
    "telephone": {"telephone": True, "target_lufs": -18.0},
    "raw": {},
}


# --- Public entry points ------------------------------------------------------


def process_voice(
    data: bytes,
    *,
    params: dict[str, Any] | None = None,
    preset: str | None = None,
    export_format: str = "mp3",
) -> tuple[bytes, dict[str, Any]]:
    """Run the enhancement chain over audio bytes; return (audio, report)."""
    chain = VoiceChain()
    if preset:
        preset = preset.lower()
        if preset not in CHAIN_PRESETS:
            raise VoiceError(
                f"Unknown preset '{preset}'. Known: {sorted(CHAIN_PRESETS)}"
            )
        chain = _from_params(CHAIN_PRESETS[preset])
    if params:
        overrides = _from_params(params)
        for key in KNOWN_CHAIN_STEPS:
            setattr(chain, key, getattr(overrides, key))
    samples, sr = decode_to_pcm(data)
    original_peak = float(np.max(np.abs(samples)))

    if chain.highpass_hz > 0:
        samples = _highpass(samples, chain.highpass_hz, sr)
    if chain.gate_db is not None:
        samples = _noise_gate(samples, chain.gate_db)
    if chain.de_ess > 0:
        samples = _de_ess(samples, sr, min(1.0, chain.de_ess))
    if (chain.eq_low, chain.eq_mid, chain.eq_high) != (1.0, 1.0, 1.0):
        samples = _eq_bands(samples, sr, chain.eq_low, chain.eq_mid, chain.eq_high)
    if chain.telephone:
        samples = _telephone(samples, sr)
    if chain.compressor_ratio > 1.0:
        samples = _compress(
            samples, chain.compressor_ratio, chain.compressor_threshold_db
        )
    if chain.reverb_mix > 0:
        samples = _reverb_send(samples, sr, min(1.0, chain.reverb_mix))
    samples = _normalize_loudness(samples, chain.target_lufs)
    samples = _fade(samples, sr, chain.fade_in, chain.fade_out)

    out = encode_pcm(samples, sr, export_format)
    final_peak = float(np.max(np.abs(samples)))
    report = {
        "duration_seconds": round(len(samples) / sr, 3),
        "input_peak": round(original_peak, 4),
        "output_peak": round(final_peak, 4),
        "target_lufs": chain.target_lufs,
        "preset": preset,
        "format": export_format,
        "steps_applied": [
            name
            for name, active in [
                ("highpass", chain.highpass_hz > 0),
                ("gate", chain.gate_db is not None),
                ("de_ess", chain.de_ess > 0),
                ("eq", (chain.eq_low, chain.eq_mid, chain.eq_high) != (1.0, 1.0, 1.0)),
                ("telephone", chain.telephone),
                ("compressor", chain.compressor_ratio > 1.0),
                ("reverb", chain.reverb_mix > 0),
                ("loudness", True),
                ("fade", True),
            ]
            if active
        ],
    }
    return out, report


def duck_music(voice: bytes, music: bytes, *, duck_db: float = -12.0) -> bytes:
    """Mix a music bed under the voice with sidechain-style ducking."""
    v, sr = decode_to_pcm(voice)
    m, _ = decode_to_pcm(music)
    n = max(len(v), len(m))
    v_pad = np.pad(v, (0, n - len(v)))
    m_pad = np.pad(m, (0, n - len(m)))

    env = np.abs(v_pad)
    env = np.convolve(env, _moving_average(2205), mode="same")  # ~50 ms
    peak = env.max() or 1.0
    duck = 1.0 + (10 ** (duck_db / 20.0) - 1.0) * np.clip(env / peak, 0.0, 1.0)
    mixed = v_pad + m_pad * duck * 0.6
    peak_out = np.max(np.abs(mixed)) or 1.0
    if peak_out > 0.99:
        mixed = mixed * (0.99 / peak_out)
    return encode_pcm(mixed.astype(np.float32), sr, "mp3")
