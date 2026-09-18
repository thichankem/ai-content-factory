"""Auto thumbnail generation plus a heuristic CTR prediction.

Best frames are chosen with the vision layer's :func:`score_best_frame`, each
is extracted as a JPG, and an optional text overlay is drawn with Pillow. A
small logistic-ish heuristic predicts a click-through rate from the frame score
and whether an overlay is present.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .vision import score_best_frame


@dataclass(frozen=True)
class ThumbnailCandidate:
    """One generated thumbnail and its predicted performance."""

    path: str
    timestamp_seconds: float
    score: float
    ctr_prediction: float


def _extract_frame(video_path: str, timestamp_seconds: float) -> np.ndarray:
    """Seek to ``timestamp_seconds`` and return one BGR frame."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"cannot open video '{video_path}'")
    try:
        cap.set(cv2.CAP_PROP_POS_MSEC, timestamp_seconds * 1000.0)
        ok, frame = cap.read()
    finally:
        cap.release()
    if not ok or frame is None:
        raise ValueError(f"no frame read at {timestamp_seconds}s from '{video_path}'")
    return np.asarray(frame)


def _draw_overlay(frame: np.ndarray, text: str) -> np.ndarray:
    """Draw ``text`` centred at the bottom of the frame and return a BGR frame."""
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(rgb)
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    width, height = img.size
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = max(0, (width - text_width) // 2)
    y = height - text_height - 10
    draw.rectangle(
        [x - 4, y - 4, x + text_width + 4, y + text_height + 4], fill=(0, 0, 0)
    )
    draw.text((x, y), text, fill=(255, 255, 255), font=font)
    return np.asarray(cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR))


def predict_ctr(score: float, has_overlay: bool) -> float:
    """Predict a click-through rate (0..1) from a frame score and overlay flag."""
    raw = 0.3 + 0.4 * score + (0.1 if has_overlay else 0.0)
    return float(max(0.0, min(1.0, raw)))


def generate_thumbnails(
    video_path: str,
    out_dir: str,
    *,
    top_k: int = 3,
    overlays: tuple[str, ...] = (),
) -> list[ThumbnailCandidate]:
    """Write the ``top_k`` best frames of ``video_path`` as JPG thumbnails.

    Best frames come from :func:`content_factory.vision.score_best_frame`. When
    ``overlays`` is non-empty the first overlay text is drawn at the bottom of
    each thumbnail. Candidates are returned sorted by ``ctr_prediction``
    descending.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    best = score_best_frame(video_path, top_k=max(1, top_k))
    has_overlay = bool(overlays)
    candidates: list[ThumbnailCandidate] = []
    for index, frame_score in enumerate(best):
        frame = _extract_frame(video_path, frame_score.timestamp_seconds)
        if has_overlay:
            frame = _draw_overlay(frame, overlays[0])
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        dest = out / f"thumbnail_{index:02d}.jpg"
        img.save(dest, "JPEG", quality=90)
        ctr = predict_ctr(frame_score.score, has_overlay)
        candidates.append(
            ThumbnailCandidate(
                path=str(dest),
                timestamp_seconds=frame_score.timestamp_seconds,
                score=frame_score.score,
                ctr_prediction=ctr,
            )
        )
    candidates.sort(key=lambda candidate: candidate.ctr_prediction, reverse=True)
    return candidates
