"""Tests for the Audition-style voice engine (real ffmpeg + numpy DSP)."""

from __future__ import annotations

import math
import subprocess

import numpy as np
import pytest

from content_factory.voice_engine import (
    CHAIN_PRESETS,
    KNOWN_CHAIN_STEPS,
    VoiceError,
    decode_to_pcm,
    duck_music,
    encode_pcm,
    process_voice,
)


def _tone_wav(seconds: float = 1.0, freq: float = 220.0) -> bytes:
    """A speech-ish test signal: tone + harmonics + noise floor."""
    sr = 44100
    t = np.linspace(0, seconds, int(sr * seconds), endpoint=False)
    signal = (
        0.3 * np.sin(2 * math.pi * freq * t)
        + 0.1 * np.sin(2 * math.pi * freq * 2 * t)
        + 0.02 * np.random.randn(len(t))
    )
    pcm = signal.astype(np.float32).tobytes()
    return subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "f32le",
            "-ac",
            "1",
            "-ar",
            str(sr),
            "-i",
            "-",
            "-y",
            "-f",
            "wav",
            "-",
        ],
        input=pcm,
        capture_output=True,
        check=True,
    ).stdout


def test_chain_presets_and_steps_are_documented() -> None:
    assert {"podcast", "voiceover", "soft", "telephone", "raw"} <= set(CHAIN_PRESETS)
    assert "target_lufs" in KNOWN_CHAIN_STEPS
    assert "compressor_ratio" in KNOWN_CHAIN_STEPS


def test_process_voice_podcast_roundtrip() -> None:
    wav = _tone_wav(1.2)
    audio, report = process_voice(wav, preset="podcast")
    assert len(audio) > 1000
    assert report["format"] == "mp3"
    assert "highpass" in report["steps_applied"]
    assert "compressor" in report["steps_applied"]
    assert "loudness" in report["steps_applied"]
    assert report["duration_seconds"] == pytest.approx(1.2, abs=0.1)


def test_process_voice_custom_params() -> None:
    wav = _tone_wav(0.8)
    _, report = process_voice(
        wav,
        params={
            "highpass_hz": 120.0,
            "gate_db": None,  # disable gate
            "de_ess": 0.0,
            "target_lufs": -14.0,
            "reverb_mix": 0.15,
            "telephone": False,
        },
    )
    assert report["target_lufs"] == -14.0
    assert "gate" not in report["steps_applied"]
    assert "de_ess" not in report["steps_applied"]
    assert "reverb" in report["steps_applied"]


def test_unknown_preset_raises() -> None:
    with pytest.raises(VoiceError, match="Unknown preset"):
        process_voice(_tone_wav(0.3), preset="hypernova")


def test_garbage_audio_raises() -> None:
    with pytest.raises(VoiceError, match="Cannot decode|Empty"):
        process_voice(b"not audio at all")


def test_encode_decode_roundtrip_preserves_duration() -> None:
    wav = _tone_wav(0.7)
    samples, sr = decode_to_pcm(wav)
    mp3 = encode_pcm(samples, sr, "mp3")
    back, sr2 = decode_to_pcm(mp3)
    assert sr2 == sr
    assert len(back) / sr2 == pytest.approx(0.7, abs=0.15)


def test_duck_music_mixes_and_returns_audio() -> None:
    voice = _tone_wav(1.0, freq=220)
    music = _tone_wav(1.4, freq=110)
    mixed = duck_music(voice, music, duck_db=-10.0)
    samples, _ = decode_to_pcm(mixed)
    assert len(samples) / 44100 == pytest.approx(1.4, abs=0.2)
