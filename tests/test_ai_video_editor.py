from __future__ import annotations

import shutil
import subprocess

import cv2
import numpy as np
import pytest

from content_factory.ai_video_editor import AiVideoEditor, _imwrite


@pytest.fixture
def media(tmp_path):
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg not installed")
    # Short clip with a moving square + audio.
    raw = tmp_path / "raw.mp4"
    writer = cv2.VideoWriter(str(raw), cv2.VideoWriter_fourcc(*"mp4v"), 15, (360, 640))
    for i in range(60):
        frame = np.full((640, 360, 3), 20, dtype=np.uint8)
        cv2.rectangle(frame, (0, 520), (360, 610), (60, 60, 90), -1)
        x = 40 + i * 3
        cv2.rectangle(frame, (x, 300), (x + 40, 340), (0, 0, 200), -1)
        writer.write(frame)
    writer.release()
    video = tmp_path / "source.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(raw),
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=330:duration=4",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-c:a",
            "aac",
            "-shortest",
            str(video),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    img = np.full((80, 120, 3), 30, dtype=np.uint8)
    cv2.circle(img, (60, 40), 30, (0, 200, 255), -1)
    logo = tmp_path / "logo.png"
    _imwrite(logo, img)
    return video, logo


def test_ai_editor_heuristic_produces_video_with_audio(media, tmp_path) -> None:
    video, logo = media
    out = tmp_path / "edited.mp4"
    report = AiVideoEditor(working_width=360).edit(video, logo, out)
    assert report.planner == "heuristic"
    assert report.placement is not None
    assert report.output_frames > 0
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=codec_type",
            "-of",
            "csv",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    types = [line.split(",")[-1] for line in probe.stdout.strip().splitlines()]
    assert "video" in types and "audio" in types


def test_ai_editor_vision_planner_is_used(media, tmp_path) -> None:
    from content_factory.ai_video_editor import _demo_vision_planner

    video, logo = media
    out = tmp_path / "edited_vision.mp4"
    report = AiVideoEditor(vision=_demo_vision_planner, working_width=360).edit(
        video, logo, out
    )
    assert report.planner == "vision"
    assert report.placement is not None
    assert report.placement.reason == "vision demo: upper-right quadrant"
