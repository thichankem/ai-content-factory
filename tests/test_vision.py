"""Pluggable vision layer: scene-cut detection and best-frame scoring."""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from content_factory.config import Settings
from content_factory.vision import (
    HeuristicSceneScorer,
    build_scorer,
    detect_scene_cuts,
    score_best_frame,
)


@pytest.fixture
def two_scene_video(tmp_path):
    """A 4s clip: 2s black then 2s white (a clean scene boundary)."""
    path = tmp_path / "scenes.avi"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 15, (160, 90))
    for _ in range(30):
        writer.write(np.zeros((90, 160, 3), dtype=np.uint8))
    for _ in range(30):
        writer.write(np.full((90, 160, 3), 255, dtype=np.uint8))
    writer.release()
    return path


@pytest.fixture
def sharp_video(tmp_path):
    """A clip where one frame is sharp and high-contrast amid uniform frames."""
    path = tmp_path / "sharp.avi"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 15, (160, 90))
    for i in range(30):
        frame = np.full((90, 160, 3), 40, dtype=np.uint8)
        if i == 10:
            cv2.rectangle(frame, (10, 10), (150, 80), (255, 255, 255), -1)
            cv2.rectangle(frame, (40, 30), (120, 60), (0, 0, 0), -1)
        writer.write(frame)
    writer.release()
    return path


def test_detect_scene_cuts_finds_the_boundary(two_scene_video) -> None:
    cuts = detect_scene_cuts(two_scene_video, threshold=30.0)
    assert len(cuts) >= 1
    # The boundary sits near the 2s midpoint.
    assert any(abs(c.start_seconds - 2.0) < 0.5 for c in cuts)


def test_detect_scene_cuts_pixel_method(two_scene_video) -> None:
    cuts = detect_scene_cuts(two_scene_video, method="pixel", threshold=30.0)
    assert len(cuts) >= 1


def test_detect_scene_cuts_rejects_missing_file(tmp_path) -> None:
    with pytest.raises(ValueError):
        detect_scene_cuts(tmp_path / "missing.avi")


def test_score_best_frame_returns_top_k(two_scene_video) -> None:
    best = score_best_frame(two_scene_video, top_k=2)
    assert len(best) == 2
    assert best[0].score >= best[1].score
    assert best[0].timestamp_seconds >= 0.0


def test_heuristic_scorer_prefers_sharp_frame(sharp_video) -> None:
    best = score_best_frame(sharp_video, top_k=1)
    # The sharp frame (index 10) should win over the uniform ones.
    assert best[0].frame_index == 10
    assert "sharp" in best[0].reason


def test_build_scorer_returns_heuristic_by_default() -> None:
    settings = Settings()
    scorer = build_scorer(settings)
    assert isinstance(scorer, HeuristicSceneScorer)


def test_build_scorer_prefers_vision_when_enabled() -> None:
    settings = Settings(enable_vision=True)

    class FakeVision:
        def score(self, frame: np.ndarray) -> tuple[float, str]:
            return 1.0, "vision"

    scorer = build_scorer(settings, vision_scorer=FakeVision())  # type: ignore[arg-type]
    assert isinstance(scorer, FakeVision)
