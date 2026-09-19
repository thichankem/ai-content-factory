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
        "highpass",
        "lowpass",
        "bandpass",
        "notch",
        "lowshelf",
        "highshelf",
        "expander",
        "de_esser",
        "clipper",
        "saturation",
        "delay",
        "echo",
        "chorus",
        "flanger",
        "phaser",
        "distortion",
        "bitcrusher",
        "tremolo",
        "vibrato",
        "ring_modulation",
        "telephone",
        "radio",
        "megaphone",
        "underwater",
        "robot",
        "reverse",
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


def _tone(sr: int, freq: float, amp: float = 0.5) -> np.ndarray:
    t = np.arange(sr, dtype=np.float32) / sr
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def test_lowpass_rejects_highs_and_keeps_lows() -> None:
    """``lowpass`` must attenuate above its cutoff, not below it.

    It used to be wired to the *high-pass* coefficients, so it did the exact
    opposite of its name.
    """
    sr = 44100
    low = _tone(sr, 200)
    high = _tone(sr, 12000)
    out_low = apply_audio_effect(low, sr, "lowpass", {"freq": 1000})
    out_high = apply_audio_effect(high, sr, "lowpass", {"freq": 1000})
    assert float(np.sqrt(np.mean(out_low**2))) > 0.5 * float(np.sqrt(np.mean(low**2)))
    assert float(np.sqrt(np.mean(out_high**2))) < 0.1 * float(np.sqrt(np.mean(high**2)))


def test_highpass_rejects_lows_and_keeps_highs() -> None:
    sr = 44100
    low = _tone(sr, 200)
    high = _tone(sr, 12000)
    out_low = apply_audio_effect(low, sr, "highpass", {"freq": 1000})
    out_high = apply_audio_effect(high, sr, "highpass", {"freq": 1000})
    assert float(np.sqrt(np.mean(out_low**2))) < 0.1 * float(np.sqrt(np.mean(low**2)))
    assert float(np.sqrt(np.mean(out_high**2))) > 0.5 * float(np.sqrt(np.mean(high**2)))


def test_telephone_is_band_limited() -> None:
    """The telephone band (300-3400 Hz) must reject audio *above* 3400 Hz."""
    sr = 44100
    mid = apply_audio_effect(_tone(sr, 1000), sr, "telephone", {})
    high = apply_audio_effect(_tone(sr, 12000), sr, "telephone", {})
    assert float(np.sqrt(np.mean(mid**2))) > 0.1
    assert float(np.sqrt(np.mean(high**2))) < float(np.sqrt(np.mean(mid**2))) * 0.2


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
