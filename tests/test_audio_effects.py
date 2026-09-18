"""Tests for the pure-NumPy audio DSP effects."""

from __future__ import annotations

import numpy as np
import pytest

from content_factory.audio_effects import (
    AudioEffectError,
    apply_audio_effect,
    audio_effect_catalog,
    audio_effect_names,
)


@pytest.fixture
def samples() -> np.ndarray:
    """A 1-second 440 Hz sine at 44.1 kHz, plus a quiet tail."""
    sr = 44100
    t = np.arange(sr, dtype=np.float32) / sr
    sig = 0.5 * np.sin(2 * np.pi * 440 * t)
    sig[int(sr * 0.7) :] *= 0.02  # quiet tail
    return sig


def test_all_effects_registered() -> None:
    for name in (
        "equalizer",
        "compressor",
        "limiter",
        "reverb",
        "voice_changer",
        "noise_gate",
    ):
        assert name in audio_effect_names()


def test_unknown_effect_raises(samples: np.ndarray) -> None:
    with pytest.raises(AudioEffectError, match="Unknown effect"):
        apply_audio_effect(samples, 44100, "nope")


def test_each_effect_keeps_length(samples: np.ndarray) -> None:
    for name in audio_effect_names():
        out = apply_audio_effect(samples, 44100, name, {})
        assert out.shape == samples.shape
        assert out.dtype == np.float32


def test_equalizer_changes_amplitude(samples: np.ndarray) -> None:
    out = apply_audio_effect(samples, 44100, "equalizer", {"bass_db": 12})
    assert float(np.max(np.abs(out))) > float(np.max(np.abs(samples)))


def test_limiter_caps_peak() -> None:
    loud = np.full(44100, 2.0, dtype=np.float32)
    out = apply_audio_effect(loud, 44100, "limiter", {"ceiling_db": -3})
    assert float(np.max(np.abs(out))) <= 10.0 ** (-3 / 20) + 1e-6


def test_noise_gate_silences_quiet_tail(samples: np.ndarray) -> None:
    out = apply_audio_effect(samples, 44100, "noise_gate", {"threshold_db": -30})
    tail = out[int(44100 * 0.7) :]
    assert float(np.max(np.abs(tail))) < 0.01


def test_voice_changer_pitch_up(samples: np.ndarray) -> None:
    out = apply_audio_effect(samples, 44100, "voice_changer", {"semitones": 12})
    assert out.shape[0] < samples.shape[0]  # pitched up -> shorter


def test_reverb_adds_tail(samples: np.ndarray) -> None:
    out = apply_audio_effect(samples, 44100, "reverb", {"amount": 0.5, "decay": 0.6})
    # Wet tail extends energy past the dry signal's end.
    assert float(np.max(np.abs(out[int(44100 * 0.95) :]))) > 1e-4


def test_catalog_has_descriptions() -> None:
    cat = audio_effect_catalog()
    names = {e["name"] for e in cat["effects"]}
    assert "compressor" in names
    for entry in cat["effects"]:
        assert entry["description"]


def test_rejects_non_mono() -> None:
    stereo = np.zeros((100, 2), dtype=np.float32)
    with pytest.raises(AudioEffectError, match="mono"):
        apply_audio_effect(stereo, 44100, "reverb")
