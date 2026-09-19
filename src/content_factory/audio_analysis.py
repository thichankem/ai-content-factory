"""Audio analysis — pure NumPy measurements of a mono PCM signal.

Everything a non-vision editor needs to *see* a clip is turned into numbers and
text here: the waveform (RMS envelope), a spectrogram, a frequency spectrum,
loudness/RMS/dynamic-range meters, clipping and peak detection, phase
correlation, and noise-floor estimation. No model, no vision, fully offline.

Functions operate on float32 mono PCM so they are trivially testable on
synthetic signals; :func:`analyze_samples` bundles the common ones into one
plain-data report.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

__all__ = [
    "analyze_samples",
    "clipping",
    "dynamic_range",
    "frequency_spectrum",
    "noise_floor",
    "phase_correlation",
    "rms",
    "spectrogram",
    "waveform",
]


def rms(
    samples: np.ndarray, frame_seconds: float = 0.023, sr: int = 44100
) -> tuple[np.ndarray, float]:
    """RMS envelope over short windows, in linear amplitude."""
    hop = max(1, round(frame_seconds * sr))
    frames = max(1, len(samples) // hop)
    env = np.empty(frames, dtype=np.float32)
    for i in range(frames):
        chunk = samples[i * hop : (i + 1) * hop]
        env[i] = float(np.sqrt(np.mean(chunk**2))) if chunk.size else 0.0
    return env, frame_seconds


def waveform(samples: np.ndarray, buckets: int = 200) -> dict[str, Any]:
    """Waveform: peak/min/max per bucket, for drawing or for text."""
    if len(samples) == 0:
        return {"buckets": 0, "peaks": [], "min": [], "max": []}
    buckets = max(1, min(buckets, len(samples)))
    edges = np.linspace(0, len(samples), buckets + 1).astype(int)
    peaks, mins, maxs = [], [], []
    for i in range(buckets):
        chunk = samples[edges[i] : edges[i + 1]]
        if chunk.size == 0:
            continue
        peaks.append(float(np.max(np.abs(chunk))))
        mins.append(float(np.min(chunk)))
        maxs.append(float(np.max(chunk)))
    return {
        "buckets": len(peaks),
        "peaks": peaks,
        "min": mins,
        "max": maxs,
        "peak_amplitude": max(peaks) if peaks else 0.0,
    }


def _stft(samples: np.ndarray, window: int = 1024, hop: int = 256) -> np.ndarray:
    """Magnitude spectrogram (dB) via a Hann-windowed STFT."""
    if len(samples) < window:
        samples = np.pad(samples, (0, window - len(samples)))
    hann = np.hanning(window)
    frames = 1 + (len(samples) - window) // hop
    spec = np.zeros((window // 2 + 1, frames), dtype=np.float32)
    for i in range(frames):
        frame = samples[i * hop : i * hop + window] * hann
        mag = np.abs(np.fft.rfft(frame))
        spec[:, i] = mag[: window // 2 + 1]
    return spec


def spectrogram(samples: np.ndarray, sr: int = 44100) -> dict[str, Any]:
    """Spectrogram as a downsampled dB matrix plus axis metadata."""
    spec = _stft(samples)
    spec_db = 20.0 * np.log10(spec + 1e-9)
    # Downsample for a compact report.
    target = 64
    if spec_db.shape[1] > target:
        idx = np.linspace(0, spec_db.shape[1] - 1, target).astype(int)
        spec_db = spec_db[:, idx]
    freqs = np.linspace(0, sr / 2, spec_db.shape[0])
    return {
        "freq_bins": spec_db.shape[0],
        "time_buckets": spec_db.shape[1],
        "sample_rate": sr,
        "max_db": float(np.max(spec_db)),
        "min_db": float(np.min(spec_db)),
        "matrix": spec_db.tolist(),
        "freq_labels": [round(float(f), 0) for f in freqs[:: max(1, len(freqs) // 8)]],
    }


def frequency_spectrum(samples: np.ndarray, sr: int = 44100) -> dict[str, Any]:
    """Average frequency spectrum with dominant-frequency detection."""
    window = min(len(samples), 4096)
    if len(samples) < window:
        samples = np.pad(samples, (0, window - len(samples)))
    mag = np.abs(np.fft.rfft(samples[:window] * np.hanning(window)))
    freqs = np.fft.rfftfreq(window, 1.0 / sr)
    # Summarise into octave-ish bands for readability.
    bands = [
        (20, 60),
        (60, 250),
        (250, 500),
        (500, 1000),
        (1000, 4000),
        (4000, 8000),
        (8000, 16000),
    ]
    band_energy = []
    for lo, hi in bands:
        mask = (freqs >= lo) & (freqs < hi)
        band_energy.append(float(np.sum(mag[mask])) if mask.any() else 0.0)
    peak_idx = int(np.argmax(mag[1:])) + 1  # skip the DC bin
    return {
        "bands": [
            {"name": f"{lo}-{hi}Hz", "energy": round(e, 3)}
            for (lo, hi), e in zip(bands, band_energy, strict=True)
        ],
        "dominant_freq_hz": round(float(freqs[peak_idx]), 1),
        "peak_magnitude": round(float(mag[peak_idx]), 3),
    }


def dynamic_range(samples: np.ndarray) -> dict[str, Any]:
    """Crest factor and dynamic range of the signal."""
    peak = float(np.max(np.abs(samples))) or 1e-9
    rms_val = float(np.sqrt(np.mean(samples**2))) or 1e-9
    crest_db = 20.0 * math.log10(peak / rms_val)
    return {
        "peak": round(peak, 4),
        "rms": round(rms_val, 4),
        "crest_factor_db": round(crest_db, 2),
        "dynamic_range_db": round(
            max(0.0, 20.0 * math.log10(peak / (np.min(np.abs(samples)) + 1e-9))), 2
        ),
    }


def clipping(samples: np.ndarray, threshold: float = 0.999) -> dict[str, Any]:
    """Detect samples pinned at the rails (potential clipping)."""
    clipped = np.count_nonzero(np.abs(samples) >= threshold)
    return {
        "clipped_samples": int(clipped),
        "clipped_ratio": round(clipped / max(1, len(samples)), 5),
        "clipping": clipped > max(10, len(samples) * 0.001),
    }


def noise_floor(
    samples: np.ndarray, percentile: float = 10.0, sr: int = 44100
) -> dict[str, Any]:
    """Estimate the noise floor from the quietest RMS percentiles."""
    env, _ = rms(samples, sr=sr)
    if env.size == 0:
        return {"noise_floor_db": None, "signal_to_noise_db": None}
    floor = float(np.percentile(env, percentile)) or 1e-9
    peak = float(np.max(env)) or 1e-9
    return {
        "noise_floor_db": round(20.0 * math.log10(floor), 2),
        "signal_to_noise_db": round(20.0 * math.log10(peak / floor), 2),
    }


def phase_correlation(samples: np.ndarray) -> dict[str, Any]:
    """Phase correlation of a mono signal against a delayed copy (0..1)."""
    if len(samples) < 2:
        return {"phase_correlation": 1.0}
    delay = max(1, len(samples) // 100)
    a = samples[:-delay]
    b = samples[delay:]
    denom = (float(np.sqrt(np.sum(a**2) * np.sum(b**2)))) or 1e-9
    corr = float(np.dot(a, b)) / denom
    return {"phase_correlation": round(max(-1.0, min(1.0, corr)), 3)}


def analyze_samples(samples: np.ndarray, sr: int = 44100) -> dict[str, Any]:
    """Bundle the common analyses into one plain-data report."""
    return {
        "length_seconds": round(len(samples) / max(1, sr), 3),
        "sample_rate": sr,
        "waveform": waveform(samples),
        "dynamic_range": dynamic_range(samples),
        "clipping": clipping(samples),
        "noise_floor": noise_floor(samples, sr=sr),
        "frequency": frequency_spectrum(samples, sr),
        "spectrogram": spectrogram(samples, sr),
        "phase_correlation": phase_correlation(samples),
    }
