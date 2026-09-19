"""Tests for the audio analysis module (waveform, spectrogram, meters)."""

from __future__ import annotations

import numpy as np

from content_factory import audio_analysis


def _sine(sr=44100, freq=440, seconds=1.0, amp=0.5) -> np.ndarray:
    t = np.arange(int(sr * seconds), dtype=np.float32) / sr
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def test_waveform_shape() -> None:
    w = audio_analysis.waveform(_sine(), buckets=50)
    assert w["buckets"] == 50
    assert len(w["peaks"]) == 50
    assert w["peak_amplitude"] > 0


def test_spectrogram_matrix() -> None:
    s = audio_analysis.spectrogram(_sine())
    assert s["freq_bins"] > 0
    assert s["time_buckets"] > 0
    assert s["max_db"] > s["min_db"]


def test_frequency_spectrum_detects_dominant() -> None:
    f = audio_analysis.frequency_spectrum(_sine(freq=440))
    assert abs(f["dominant_freq_hz"] - 440) < 60


def test_rms_and_dynamic_range() -> None:
    sig = _sine()
    dr = audio_analysis.dynamic_range(sig)
    assert dr["peak"] > 0
    assert dr["rms"] > 0
    assert dr["crest_factor_db"] > 0


def test_clipping_detection() -> None:
    loud = np.full(44100, 1.5, dtype=np.float32)
    assert audio_analysis.clipping(loud)["clipping"] is True
    quiet = _sine(amp=0.2)
    assert audio_analysis.clipping(quiet)["clipping"] is False


def test_noise_floor() -> None:
    sig = _sine(seconds=2.0)
    sig[22050:] = 0.0  # quiet second half
    nf = audio_analysis.noise_floor(sig)
    assert nf["noise_floor_db"] is not None
    assert nf["signal_to_noise_db"] > 0


def test_phase_correlation() -> None:
    sig = _sine()
    pc = audio_analysis.phase_correlation(sig)
    assert -1.0 <= pc["phase_correlation"] <= 1.0


def test_analyze_samples_bundle() -> None:
    report = audio_analysis.analyze_samples(_sine())
    for key in (
        "waveform",
        "dynamic_range",
        "clipping",
        "noise_floor",
        "frequency",
        "spectrogram",
    ):
        assert key in report
