"""Pluggable audio perception layer: silence/pace, music mood, audio quality."""

from __future__ import annotations

import math
import wave

import numpy as np
import pytest

from content_factory.config import Settings
from content_factory.perception import (
    AudioPerception,
    build_audio_perception,
    check_audio_quality,
    classify_music_mood,
    detect_silence_and_pace,
)


def _write_wav(path, samples: np.ndarray, rate: int = 22050) -> None:
    """Write mono float32 samples in ``[-1, 1]`` to a 16-bit WAV file."""
    pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(pcm.tobytes())


@pytest.fixture
def silence_then_tone(tmp_path):
    """2s of digital silence followed by 2s of a steady tone."""
    rate = 22050
    silence = np.zeros(rate * 2, dtype=np.float32)
    t = np.arange(rate * 2) / rate
    tone = (0.5 * np.sin(2 * math.pi * 330 * t)).astype(np.float32)
    path = tmp_path / "silence_tone.wav"
    _write_wav(path, np.concatenate([silence, tone]), rate)
    return path


@pytest.fixture
def clipped_wav(tmp_path):
    """A heavily clipped signal (constant max amplitude)."""
    rate = 22050
    samples = np.full(rate, 1.0, dtype=np.float32)
    path = tmp_path / "clipped.wav"
    _write_wav(path, samples, rate)
    return path


def test_detect_silence_and_pace_finds_the_gap(silence_then_tone) -> None:
    segments, pace = detect_silence_and_pace(silence_then_tone)
    assert pace.total_duration == pytest.approx(4.0, abs=0.2)
    assert len(segments) >= 1
    # The leading silence should start near 0s.
    assert any(seg.start_seconds < 0.3 for seg in segments)
    # Roughly half the clip is silent, so speech_ratio is well below 1.
    assert pace.speech_ratio < 0.7


def test_classify_music_mood_returns_a_real_mood(silence_then_tone) -> None:
    mood = classify_music_mood(silence_then_tone)
    assert mood.mood != "unknown"
    assert mood.energy > 0.0


def test_check_audio_quality_flags_clipping(clipped_wav) -> None:
    quality = check_audio_quality(clipped_wav)
    assert quality.clipping is True
    assert quality.peak_db >= -1.0


def test_check_audio_quality_healthy_signal_is_not_clipped(silence_then_tone) -> None:
    quality = check_audio_quality(silence_then_tone)
    assert quality.clipping is False


def test_decode_rejects_missing_file(tmp_path) -> None:
    with pytest.raises(ValueError):
        detect_silence_and_pace(tmp_path / "missing.wav")


def test_build_audio_perception_returns_facade() -> None:
    settings = Settings()
    perceiver = build_audio_perception(settings)
    assert isinstance(perceiver, AudioPerception)


def test_ai_tools_raise_when_no_backend_wired(silence_then_tone) -> None:
    perceiver = build_audio_perception(Settings())
    with pytest.raises(RuntimeError):
        perceiver.detect_audio_events(silence_then_tone)
    with pytest.raises(RuntimeError):
        perceiver.diarize_speakers(silence_then_tone)
    with pytest.raises(RuntimeError):
        perceiver.detect_speech_emotion(silence_then_tone)
    with pytest.raises(RuntimeError):
        perceiver.describe_audio_scene(silence_then_tone)


def test_ai_tools_dispatch_to_wired_backend(silence_then_tone) -> None:
    class FakeEvents:
        def detect(self, audio_path):
            return []

    class FakeDiarizer:
        def diarize(self, audio_path):
            return []

    class FakeEmotion:
        def analyze(self, audio_path):
            return type("E", (), {"emotion": "neutral", "confidence": 0.9})()

    class FakeDescriber:
        def describe(self, audio_path):
            return type("D", (), {"description": "quiet tone"})()

    perceiver = build_audio_perception(
        Settings(),
        event_detector=FakeEvents(),  # type: ignore[arg-type]
        diarizer=FakeDiarizer(),  # type: ignore[arg-type]
        emotion_analyzer=FakeEmotion(),  # type: ignore[arg-type]
        scene_describer=FakeDescriber(),  # type: ignore[arg-type]
    )
    assert perceiver.detect_audio_events(silence_then_tone) == []
    assert perceiver.diarize_speakers(silence_then_tone) == []
    assert perceiver.detect_speech_emotion(silence_then_tone).emotion == "neutral"
    assert perceiver.describe_audio_scene(silence_then_tone).description == "quiet tone"
