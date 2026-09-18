"""Production helpers: music ducking, virality scoring and thumbnails."""

from __future__ import annotations

import wave
from pathlib import Path

import cv2
import numpy as np
import pytest

from content_factory.audio import duck_music, duck_music_under_speech, ffmpeg_binary
from content_factory.thumbnail import (
    ThumbnailCandidate,
    _extract_frame,
    generate_thumbnails,
    predict_ctr,
)
from content_factory.virality import score_hook, score_virality


def _write_tone(path: Path, freq: float, amp: float, duration: float = 1.0) -> None:
    rate = 8000
    n = int(rate * duration)
    t = np.arange(n) / rate
    samples = (amp * 32000.0 * np.sin(2.0 * np.pi * freq * t)).astype(np.int16)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(samples.tobytes())


@pytest.fixture
def tiny_video(tmp_path: Path) -> Path:
    """A 2s synthetic clip: 1s grey then 1s white, with one sharp frame."""
    path = tmp_path / "clip.avi"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 15, (160, 90))
    for i in range(30):
        frame = np.full((90, 160, 3), 40, dtype=np.uint8)
        if i == 10:
            cv2.rectangle(frame, (10, 10), (150, 80), (255, 255, 255), -1)
            cv2.rectangle(frame, (40, 30), (120, 60), (0, 0, 0), -1)
        writer.write(frame)
    writer.release()
    return path


def test_ffmpeg_binary_is_available() -> None:
    assert ffmpeg_binary()


def test_duck_music_under_speech_produces_output(tmp_path: Path) -> None:
    music = tmp_path / "music.wav"
    voice = tmp_path / "voice.wav"
    out = tmp_path / "mixed.wav"
    _write_tone(music, 330.0, 0.2)
    _write_tone(voice, 660.0, 0.9)
    result = duck_music_under_speech(str(music), str(voice), str(out))
    assert result == str(out)
    assert out.exists()
    assert out.stat().st_size > 0


def test_duck_music_wrapper(tmp_path: Path) -> None:
    music = tmp_path / "music.wav"
    voice = tmp_path / "voice.wav"
    out = tmp_path / "mixed.wav"
    _write_tone(music, 261.0, 0.2)
    _write_tone(voice, 523.0, 0.9)
    duck_music(str(music), str(voice), str(out))
    assert out.exists()
    assert out.stat().st_size > 0


def test_score_hook_rates_curiosity_hook() -> None:
    short = "Why do you never share this secret?"
    long = (
        "This is a very long sentence that goes on and on about many things "
        "without ever getting to the point quickly"
    )
    assert score_hook(short) == 1.0
    assert score_hook(long) < score_hook(short)


def test_score_virality_prefers_strong_hook_and_cta() -> None:
    strong = (
        "Why do you never share this secret? Here is the answer. Follow for more tips!"
    )
    flat = (
        "This is a very long and rambling explanation that continues for many "
        "sentences without ever arriving at a clear point or asking the audience "
        "to take any action whatsoever and it just keeps going on and on forever."
    )
    strong_score = score_virality(strong)
    flat_score = score_virality(flat)
    assert strong_score.score > flat_score.score
    assert flat_score.warnings


def test_generate_thumbnails_writes_top_k(tmp_path: Path, tiny_video: Path) -> None:
    candidates = generate_thumbnails(
        str(tiny_video), str(tmp_path), top_k=3, overlays=("SUBSCRIBE",)
    )
    assert len(candidates) == 3
    assert all(isinstance(c, ThumbnailCandidate) for c in candidates)
    jpgs = sorted(tmp_path.glob("*.jpg"))
    assert len(jpgs) == 3
    for candidate in candidates:
        assert Path(candidate.path).exists()
    ctrs = [c.ctr_prediction for c in candidates]
    assert ctrs == sorted(ctrs, reverse=True)


def test_predict_ctr_is_clamped_and_boosted_by_overlay() -> None:
    assert predict_ctr(2.0, False) == 1.0
    assert predict_ctr(-1.0, False) == 0.0
    assert predict_ctr(0.5, True) > predict_ctr(0.5, False)


def test_extract_frame_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        _extract_frame(str(tmp_path / "missing.avi"), 0.5)
