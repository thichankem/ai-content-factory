"""Tests for the audio stem-separation module (voice isolation + adapters)."""

from __future__ import annotations

import math

import numpy as np

from content_factory import audio_separation


def _sig(sr=44100, seconds=1.0) -> np.ndarray:
    t = np.arange(int(sr * seconds), dtype=np.float32) / sr
    # A 440 Hz tone (mid/vocal band) plus a 60 Hz rumble (low).
    return (
        0.5 * np.sin(2 * np.pi * 440 * t) + 0.3 * np.sin(2 * np.pi * 60 * t)
    ).astype(np.float32)


def _tone(sr: int, freq: float, amp: float = 0.5, seconds: float = 1.0) -> np.ndarray:
    t = np.arange(int(sr * seconds), dtype=np.float32) / sr
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def _amplitude(signal: np.ndarray, freq: float, sr: int) -> float:
    """Peak amplitude of one frequency in a signal, phase-insensitive."""
    t = np.arange(len(signal), dtype=np.float32) / sr
    in_phase = float(np.dot(signal, np.cos(2 * np.pi * freq * t)))
    quad = float(np.dot(signal, np.sin(2 * np.pi * freq * t)))
    return 2.0 * math.hypot(in_phase, quad) / max(1, len(signal))


def test_two_stem_split() -> None:
    stems = audio_separation.separate_stems(_sig(), 44100, num=2)
    assert set(stems) == {"voice", "instrumental"}
    for v in stems.values():
        assert v.dtype == np.float32
        assert len(v) > 0


def test_voice_stem_is_band_limited() -> None:
    """The voice stem keeps 200-4000 Hz and rejects both sides of that band.

    Both the upper edge and the low band used to be high-pass filters, so the
    "voice" stem was really "everything above 4 kHz" and the raw comparison of
    two near-zero correlations below could not tell the difference.
    """
    sr = 44100
    cleaned = audio_separation.separate_stems(_sig(sr), sr, num=2)["voice"]
    # The 440 Hz tone sits inside the band and survives...
    assert _amplitude(cleaned, 440, sr) > 0.25 * _amplitude(_tone(sr, 440), 440, sr)
    # ...while the 60 Hz rumble does not.
    assert _amplitude(cleaned, 60, sr) < 0.1
    # A 12 kHz tone sits above the 4 kHz edge and must be rejected too.
    above = audio_separation.separate_stems(
        (_tone(sr, 440) + _tone(sr, 12000)).astype(np.float32), sr, num=2
    )["voice"]
    assert _amplitude(above, 12000, sr) < 0.25 * _amplitude(_tone(sr, 12000), 12000, sr)


def test_three_stem_split_assigns_the_bands() -> None:
    """low/mid/high must each keep their own band (the low stem used to be a
    high-pass, so it held everything above 250 Hz instead of below it)."""
    sr = 44100
    stems = audio_separation.separate_stems(_sig(sr), sr, num=3)
    # The 60 Hz rumble belongs to the low stem, the 440 Hz tone to the mid one.
    rumble = _amplitude(_tone(sr, 60, 0.3), 60, sr)
    tone = _amplitude(_tone(sr, 440), 440, sr)
    assert _amplitude(stems["low"], 60, sr) > 0.5 * rumble
    assert _amplitude(stems["mid"], 440, sr) > 0.25 * tone
    assert _amplitude(stems["high"], 440, sr) < 0.1


def test_three_stem_split() -> None:
    stems = audio_separation.separate_stems(_sig(), 44100, num=3)
    assert set(stems) == {"low", "mid", "high"}


def test_voice_isolation_helper() -> None:
    iso = audio_separation.voice_isolation(_sig(), 44100)
    assert iso.dtype == np.float32
    assert len(iso) > 0


def test_stem_catalog() -> None:
    cat = audio_separation.stem_catalog()
    names = {s["name"] for s in cat["stems"]}
    assert {"voice", "instrumental", "low", "mid", "high"} <= names
    for entry in cat["stems"]:
        assert entry["description"]


def test_pluggable_adapter_override() -> None:
    calls = {}

    def fake_adapter(samples: np.ndarray, sr: int) -> dict[str, np.ndarray]:
        calls["called"] = True
        return {"voice": samples * 0.0, "instrumental": samples}

    audio_separation.register_adapter("voice", fake_adapter)
    try:
        stems = audio_separation.separate_stems(_sig(), 44100, num=2)
        assert calls.get("called") is True
        assert np.all(stems["voice"] == 0)
    finally:
        audio_separation._SEPARATION_ADAPTERS.pop("voice", None)


def test_stem_catalog_reflects_adapter() -> None:
    def fake_adapter(samples: np.ndarray, sr: int) -> dict[str, np.ndarray]:
        return {"voice": samples}

    audio_separation.register_adapter("voice", fake_adapter)
    try:
        cat = audio_separation.stem_catalog()
        voice = next(s for s in cat["stems"] if s["name"] == "voice")
        assert voice["adapter"] is True
    finally:
        audio_separation._SEPARATION_ADAPTERS.pop("voice", None)
