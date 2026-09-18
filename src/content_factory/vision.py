"""Pluggable vision layer for video analysis.

Mirrors the "vision is optional" principle: the same task runs with a cheap
non-vision heuristic or, when enabled, a pluggable vision model — without
changing the calling code.

  * :func:`detect_scene_cuts` — non-vision shot-boundary detection. Compares
    consecutive frames (HSV-histogram by default, raw pixel diff as an
    alternative) and returns scene segments. No GPU, no model.
  * :func:`score_best_frame` — ranks sampled frames by quality. The default
    :class:`HeuristicSceneScorer` uses sharpness / exposure / saturation; a
    :class:`VisionSceneScorer` plugs in a multimodal model that understands
    content. The heuristic runs everywhere; vision is opt-in via config.

Both functions are pure over a video path and return plain data, so they are
testable offline and callable from the MCP server.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import cv2
import numpy as np

from .config import Settings


@dataclass(frozen=True)
class SceneCut:
    """One detected scene segment, in seconds."""

    start_seconds: float
    end_seconds: float
    score: float  # boundary strength, 0..1


@dataclass(frozen=True)
class FrameScore:
    """Quality score for one sampled frame."""

    frame_index: int
    timestamp_seconds: float
    score: float
    reason: str


class SceneScorer(Protocol):
    """A scorer that rates a single BGR frame; higher is better."""

    def score(self, frame: np.ndarray) -> tuple[float, str]: ...


class HeuristicSceneScorer:
    """No-vision quality scorer: sharpness + exposure + saturation.

    Sharpness (Laplacian variance) favours in-focus shots; exposure rewards a
    mid-toned frame; saturation rewards vivid colour. Cheap, deterministic,
    and runs anywhere.
    """

    def score(self, frame: np.ndarray) -> tuple[float, str]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        sharpness = min(1.0, lap_var / 500.0)
        mean_gray = float(gray.mean()) / 255.0
        exposure = 1.0 - abs(mean_gray - 0.5) * 2.0
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        saturation = float(hsv[:, :, 1].mean()) / 255.0
        score = 0.5 * sharpness + 0.3 * exposure + 0.2 * saturation
        reasons = []
        if sharpness >= 0.5:
            reasons.append("sharp")
        if exposure >= 0.6:
            reasons.append("well-exposed")
        if saturation >= 0.4:
            reasons.append("colourful")
        return score, ", ".join(reasons) or "neutral"


class VisionSceneScorer(Protocol):
    """A vision-capable scorer that understands frame content.

    Implementations may call a local model (YOLO/CLIP) or a multimodal LLM.
    The seam keeps the calling code unchanged: swap the scorer, not the call.
    """

    def score(self, frame: np.ndarray) -> tuple[float, str]: ...


def _frame_timestamp(frame_index: int, fps: float, sample_every: int) -> float:
    """Seconds of a sampled frame given the source frame rate and stride."""
    return round(frame_index * sample_every / max(1.0, fps), 3)


def detect_scene_cuts(
    video_path: str | Path,
    *,
    method: str = "histogram",
    threshold: float = 30.0,
    min_scene_seconds: float = 0.4,
    sample_every: int = 1,
) -> list[SceneCut]:
    """Detect shot boundaries in a video and return scene segments.

    ``method`` is ``"histogram"`` (HSV-histogram distance, default) or
    ``"pixel"`` (mean absolute pixel difference). A boundary is marked where
    the inter-frame difference exceeds ``threshold``. Segments shorter than
    ``min_scene_seconds`` are merged into their neighbours. Pure OpenCV — no
    model, no GPU.
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"cannot open video '{video_path}'")
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
    try:
        prev_hist: np.ndarray | None = None
        prev_gray: np.ndarray | None = None
        boundaries: list[int] = []
        diffs: list[float] = []
        index = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if index % sample_every != 0:
                index += 1
                continue
            if method == "pixel":
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                if prev_gray is not None:
                    diff = float(cv2.absdiff(prev_gray, gray).mean())
                    diffs.append(diff)
                    if diff > threshold:
                        boundaries.append(index)
                prev_gray = gray
            else:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
                cv2.normalize(hist, hist)
                if prev_hist is not None:
                    diff = float(
                        cv2.compareHist(prev_hist, hist, cv2.HISTCMP_BHATTACHARYYA)
                    )
                    diffs.append(diff)
                    if diff > threshold / 100.0:
                        boundaries.append(index)
                prev_hist = hist
            index += 1
    finally:
        cap.release()

    if not diffs:
        return []
    # Build segments between boundaries.
    cuts: list[SceneCut] = []
    start = 0
    for boundary in boundaries:
        end = boundary
        if end - start >= min_scene_seconds * fps:
            cuts.append(
                SceneCut(
                    start_seconds=_frame_timestamp(start, fps, sample_every),
                    end_seconds=_frame_timestamp(end, fps, sample_every),
                    score=round(0.0, 3),
                )
            )
        start = end
    if start < index:
        cuts.append(
            SceneCut(
                start_seconds=_frame_timestamp(start, fps, sample_every),
                end_seconds=_frame_timestamp(index, fps, sample_every),
                score=round(0.0, 3),
            )
        )
    return cuts


def score_best_frame(
    video_path: str | Path,
    *,
    scorer: SceneScorer | VisionSceneScorer | None = None,
    top_k: int = 1,
    sample_every: int = 1,
) -> list[FrameScore]:
    """Sample a video, score each sampled frame, and return the best ``top_k``.

    Uses :class:`HeuristicSceneScorer` by default; pass a vision scorer to
    prefer content-aware selection. Scores are returned highest first.
    """
    active: SceneScorer | VisionSceneScorer = scorer or HeuristicSceneScorer()
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"cannot open video '{video_path}'")
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
    scored: list[FrameScore] = []
    try:
        index = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if index % sample_every != 0:
                index += 1
                continue
            value, reason = active.score(frame)
            scored.append(
                FrameScore(
                    frame_index=index,
                    timestamp_seconds=_frame_timestamp(index, fps, sample_every),
                    score=round(value, 4),
                    reason=reason,
                )
            )
            index += 1
    finally:
        cap.release()

    scored.sort(key=lambda entry: entry.score, reverse=True)
    return scored[: max(1, top_k)]


def build_scorer(
    settings: Settings,
    vision_scorer: VisionSceneScorer | None = None,
) -> SceneScorer | VisionSceneScorer:
    """Pick the scorer for the configured vision mode.

    With ``enable_vision`` off (the default) or no vision scorer supplied, the
    cheap :class:`HeuristicSceneScorer` is returned. When vision is enabled and
    a scorer is wired in, it is preferred — the caller swaps the backend, not
    the call site.
    """
    if settings.enable_vision and vision_scorer is not None:
        return vision_scorer
    return HeuristicSceneScorer()
