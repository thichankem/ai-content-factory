"""AI Video Editor: analyse a video, composite an image naturally, cut, export.

The pipeline answers the "can the AI really edit a video?" test:

  1. Analyse — sample the video and understand where content sits.
  2. Plan — pick a natural position + size + time window for the inserted image
     (a vision model when one is configured, otherwise a computer-vision
     heuristic that prefers visually flat regions away from the subject).
  3. Track — follow the insertion region across frames with optical flow so the
     image moves with the camera/subject instead of floating in a fixed spot.
  4. Composite — blend the image with a feathered alpha mask (mask-based
     compositing, not a rigid overlay).
  5. Cut — trim redundant near-static segments into a clean timeline.
  6. Export — write ``final.mp4`` (H.264 + original audio) with ffmpeg.

Two planners are provided so the same pipeline runs with or without a vision
model:

  * :class:`HeuristicPlanner` — no vision model needed; uses gradient saliency
    to find a flat, natural spot.
  * :class:`VisionPlanner` — a pluggable interface for a vision LLM that can
    describe the scene and propose a placement. When a vision model is
    configured it is preferred; otherwise the heuristic is used.
"""

from __future__ import annotations

import subprocess
import tempfile
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import cv2
import numpy as np

#: Working width for analysis/tracking (frames are downscaled to keep it fast).
_WORK_WIDTH = 480
#: Fraction of the frame width the inserted image should occupy.
_IMAGE_SCALE = 0.22
#: Minimum tracked feature count before we fall back to dense flow.
_MIN_FEATURES = 4
#: Motion threshold (mean abs diff / 255) below which a segment is "dead air".
_STATIC_THRESHOLD = 0.006
#: Minimum dead-air length (seconds) worth cutting.
_MIN_CUT_SECONDS = 2.0
#: Keep at least this many seconds of a static segment.
_KEEP_STATIC_SECONDS = 1.0
#: Never remove more than this fraction of frames in one cut pass.
_MAX_CUT_FRACTION = 0.5


@dataclass
class Placement:
    """Where and when the image is inserted, in working-frame coordinates."""

    x: int
    y: int
    w: int
    h: int
    start_frame: int = 0
    end_frame: int = 0  # exclusive; 0 means "until the end"
    reason: str = ""


@dataclass
class CutRange:
    """A contiguous frame range to remove from the final cut."""

    start: int
    end: int  # exclusive


@dataclass
class EditReport:
    """Summary of an AI edit run."""

    source_frames: int
    output_frames: int
    fps: int
    placement: Placement | None
    cuts: list[CutRange] = field(default_factory=list)
    planner: str = "heuristic"
    output_path: str = ""


class VisionPlanner(Protocol):
    """A vision-capable model that proposes an image placement."""

    def plan(self, frames: list[np.ndarray], image: np.ndarray) -> Placement | None: ...


class HeuristicPlanner:
    """No-vision placement: pick a visually flat region away from the subject.

    Computes a gradient-saliency grid and chooses the lowest-complexity cell in
    the lower two-thirds, which reads as a natural spot for an inserted image
    (logos, stickers, captions) without covering the main action.
    """

    def __init__(self, grid_cols: int = 5, grid_rows: int = 4) -> None:
        self.grid_cols = grid_cols
        self.grid_rows = grid_rows

    def plan(self, frames: list[np.ndarray], image: np.ndarray) -> Placement | None:
        if not frames:
            return None
        h, w = frames[0].shape[:2]
        # Average gradient magnitude across sampled frames = per-cell complexity.
        acc = np.zeros((self.grid_rows, self.grid_cols), dtype=np.float64)
        for frame in frames[:: max(1, len(frames) // 8)][:8]:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
            gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
            mag = cv2.magnitude(gx, gy)
            cell_h, cell_w = h // self.grid_rows, w // self.grid_cols
            for r in range(self.grid_rows):
                for c in range(self.grid_cols):
                    cell = mag[
                        r * cell_h : (r + 1) * cell_h, c * cell_w : (c + 1) * cell_w
                    ]
                    acc[r, c] += float(cell.mean())
        acc /= max(1, len(frames[:: max(1, len(frames) // 8)][:8]))

        # Candidate cells: lower two-thirds, excluding the very edges.
        candidates = []
        for r in range(max(1, self.grid_rows // 3), self.grid_rows - 1):
            for c in range(1, self.grid_cols - 1):
                candidates.append((acc[r, c], r, c))
        if not candidates:
            candidates = [
                (acc[r, c], r, c)
                for r in range(self.grid_rows)
                for c in range(self.grid_cols)
            ]
        _, best_r, best_c = min(candidates, key=lambda t: t[0])

        cell_h, cell_w = h // self.grid_rows, w // self.grid_cols
        img_h, img_w = image.shape[:2]
        box_w = int(w * _IMAGE_SCALE)
        box_h = int(box_w * img_h / max(1, img_w))
        cx = best_c * cell_w + cell_w // 2
        cy = best_r * cell_h + cell_h // 2
        x = max(0, min(w - box_w, cx - box_w // 2))
        y = max(0, min(h - box_h, cy - box_h // 2))
        return Placement(
            x=x,
            y=y,
            w=box_w,
            h=box_h,
            reason=f"lowest-complexity cell ({best_r},{best_c})",
        )


def _imread(path: Path, flags: int = cv2.IMREAD_UNCHANGED) -> np.ndarray | None:
    """Read an image from a possibly non-ASCII path (Windows-safe)."""
    data = np.fromfile(str(path), dtype=np.uint8)
    if data.size == 0:
        return None
    return cv2.imdecode(data, flags)


def _imwrite(path: Path, image: np.ndarray, params: list[int] | None = None) -> bool:
    """Write an image to a possibly non-ASCII path (Windows-safe)."""
    ext = "." + path.suffix.lstrip(".").lower()
    ok, buf = cv2.imencode(ext, image, params or [])
    if not ok:
        return False
    buf.tofile(str(path))
    return True


def _track_box(
    frames: list[np.ndarray], box: tuple[int, int, int, int]
) -> list[tuple[int, int, int, int]]:
    """Track a bounding box across frames with KLT optical flow.

    Returns one box per frame (the first is the input box). Falls back to dense
    Farneback flow when too few features survive.
    """
    boxes: list[tuple[int, int, int, int]] = [box]
    x, y, w, h = box
    prev_gray = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY)
    prev_pts = _features_in_box(prev_gray, (x, y, w, h))
    for i in range(1, len(frames)):
        cur_gray = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
        dx = dy = 0.0
        if prev_pts is not None and len(prev_pts) >= _MIN_FEATURES:
            next_pts, status, _ = cv2.calcOpticalFlowPyrLK(  # type: ignore[call-overload]
                prev_gray, cur_gray, prev_pts, None
            )
            good = next_pts[status.flatten() == 1]
            if len(good) >= _MIN_FEATURES:
                dx = float(
                    np.median(good[:, 0] - prev_pts[status.flatten() == 1][:, 0])
                )
                dy = float(
                    np.median(good[:, 1] - prev_pts[status.flatten() == 1][:, 1])
                )
                prev_pts = good.reshape(-1, 1, 2)
            else:
                dx, dy = _dense_flow_delta(prev_gray, cur_gray, (x, y, w, h))
                prev_pts = _features_in_box(cur_gray, (x, y, w, h))
        else:
            dx, dy = _dense_flow_delta(prev_gray, cur_gray, (x, y, w, h))
            prev_pts = _features_in_box(cur_gray, (x, y, w, h))
        x = int(round(x + dx))
        y = int(round(y + dy))
        H, W = cur_gray.shape
        x = max(0, min(W - w, x))
        y = max(0, min(H - h, y))
        boxes.append((x, y, w, h))
        prev_gray = cur_gray
    return boxes


def _features_in_box(
    gray: np.ndarray, box: tuple[int, int, int, int]
) -> np.ndarray | None:
    x, y, w, h = box
    roi = gray[y : y + h, x : x + w]
    pts = cv2.goodFeaturesToTrack(roi, maxCorners=60, qualityLevel=0.01, minDistance=7)
    if pts is None or len(pts) == 0:
        return None
    pts = pts.reshape(-1, 2)
    pts[:, 0] = pts[:, 0] + x
    pts[:, 1] = pts[:, 1] + y
    return pts.reshape(-1, 1, 2)


def _dense_flow_delta(
    prev_gray: np.ndarray, cur_gray: np.ndarray, box: tuple[int, int, int, int]
) -> tuple[float, float]:
    x, y, w, h = box
    flow = np.asarray(
        cv2.calcOpticalFlowFarneback(  # type: ignore[call-overload]
            prev_gray,
            cur_gray,
            None,
            pyr_scale=0.5,
            levels=3,
            winsize=15,
            iterations=3,
            poly_n=5,
            poly_sigma=1.2,
            flags=0,
        )
    )
    fx = flow[y : y + h, x : x + w, 0]
    fy = flow[y : y + h, x : x + w, 1]
    return float(np.median(fx)), float(np.median(fy))


def _composite(
    frame: np.ndarray,
    image: np.ndarray,
    box: tuple[int, int, int, int],
    *,
    feather: int = 12,
) -> np.ndarray:
    """Blend ``image`` into ``frame`` at ``box`` with a feathered alpha mask."""
    x, y, w, h = box
    x = max(0, x)
    y = max(0, y)
    H, W = frame.shape[:2]
    w = min(w, W - x)
    h = min(h, H - y)
    if w <= 0 or h <= 0:
        return frame
    resized = cv2.resize(image, (w, h), interpolation=cv2.INTER_AREA)
    # Feathered alpha mask.
    mask = np.full((h, w), 255, dtype=np.uint8)
    mask = cv2.GaussianBlur(mask, (0, 0), sigmaX=feather)
    roi = frame[y : y + h, x : x + w]
    alpha = mask.astype(np.float32)[..., None] / 255.0
    blended = (
        roi.astype(np.float32) * (1.0 - alpha) + resized.astype(np.float32) * alpha
    )
    frame[y : y + h, x : x + w] = blended.astype(np.uint8)
    return frame


def _detect_cuts(frames: list[np.ndarray], fps: int) -> list[CutRange]:
    """Trim long near-static segments (dead air) into a clean timeline."""
    if len(frames) < 2:
        return []
    motion = []
    prev = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY)
    for i in range(1, len(frames)):
        cur = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
        diff = cv2.absdiff(prev, cur)
        motion.append(float(diff.mean()) / 255.0)
        prev = cur
    # Pad to align with frame indices.
    motion = [motion[0]] + motion

    cuts: list[CutRange] = []
    i = 0
    n = len(motion)
    min_len = int(_MIN_CUT_SECONDS * fps)
    keep_len = int(_KEEP_STATIC_SECONDS * fps)
    max_cut = int(n * _MAX_CUT_FRACTION)
    total_cut = 0
    while i < n:
        if motion[i] < _STATIC_THRESHOLD:
            j = i
            while j < n and motion[j] < _STATIC_THRESHOLD:
                j += 1
            seg_len = j - i
            if seg_len >= min_len:
                # Keep a short lead-in/lead-out so the cut is not jarring.
                start = i + keep_len
                end = j - keep_len
                if end > start:
                    cut_len = end - start
                    if total_cut + cut_len <= max_cut:
                        cuts.append(CutRange(start=start, end=end))
                        total_cut += cut_len
            i = j
        else:
            i += 1
    return cuts


def _export(
    frames: list[np.ndarray],
    fps: int,
    output_path: Path,
    audio_path: Path | None = None,
    ffmpeg_binary: str | None = None,
) -> Path:
    """Write frames to a temp dir and mux with ffmpeg into final.mp4."""
    binary = ffmpeg_binary or "ffmpeg"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="cf-edit-") as tmp:
        tmpdir = Path(tmp)
        for idx, frame in enumerate(frames):
            _imwrite(tmpdir / f"f_{idx:05d}.jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
        cmd = [
            binary,
            "-y",
            "-framerate",
            str(fps),
            "-i",
            str(tmpdir / "f_%05d.jpg"),
        ]
        if audio_path is not None and audio_path.is_file():
            cmd += ["-i", str(audio_path), "-c:a", "aac", "-shortest"]
        cmd += [
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise RuntimeError(
                proc.stderr.strip().splitlines()[-1:] or ["ffmpeg failed"]
            )
    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise RuntimeError("ffmpeg finished without creating the output file.")
    return output_path


class AiVideoEditor:
    """Coordinates the full AI edit: analyse -> plan -> track -> composite -> cut."""

    def __init__(
        self,
        *,
        vision: (
            VisionPlanner | Callable[[list[np.ndarray], np.ndarray], Placement | None]
        )
        | None = None,
        planner: Callable[[list[np.ndarray], np.ndarray], Placement | None]
        | None = None,
        working_width: int = _WORK_WIDTH,
    ) -> None:
        self._vision: (
            VisionPlanner
            | Callable[[list[np.ndarray], np.ndarray], Placement | None]
            | None
        ) = vision
        self._heuristic = HeuristicPlanner()
        self._planner = planner
        self._working_width = working_width

    def edit(
        self,
        video_path: Path,
        image_path: Path,
        output_path: Path,
        *,
        ffmpeg_binary: str | None = None,
        cut: bool = True,
        audio_path: Path | None = None,
    ) -> EditReport:
        """Run the full edit and return a report."""
        image = _imread(image_path)
        if image is None:
            raise ValueError(f"cannot read image '{image_path}'")
        # Preserve the source audio automatically when none is supplied.
        auto_audio: Path | None = None
        if audio_path is None:
            auto_audio = (
                Path(tempfile.gettempdir()) / f"cf-edit-audio-{uuid.uuid4().hex}.m4a"
            )
            audio_path = extract_audio(video_path, auto_audio)
        if image.shape[2] == 4:
            # Straight alpha onto white so downstream compositing is predictable.
            bgr = image[:, :, :3]
            alpha = image[:, :, 3:4].astype(np.float32) / 255.0
            image = (bgr.astype(np.float32) * alpha + 255.0 * (1 - alpha)).astype(
                np.uint8
            )

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"cannot open video '{video_path}'")
        fps = int(cap.get(cv2.CAP_PROP_FPS) or 30)
        src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        scale = self._working_width / max(1, src_w)
        work_h = int(src_h * scale)
        # libx264 + yuv420p need even dimensions.
        if work_h % 2:
            work_h -= 1

        # 1+2. Analyse + plan placement.
        frames: list[np.ndarray] = []
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if scale != 1.0:
                frame = cv2.resize(
                    frame, (self._working_width, work_h), interpolation=cv2.INTER_AREA
                )
            frames.append(frame)
        cap.release()
        if not frames:
            raise ValueError("video has no readable frames")

        placement = None
        planner_name = "heuristic"
        if self._planner is not None:
            placement = self._planner(frames, image)
            planner_name = "custom"
        elif self._vision is not None:
            if callable(self._vision):
                placement = self._vision(frames, image)
            else:
                placement = self._vision.plan(frames, image)
            planner_name = "vision"
        if placement is None:
            placement = self._heuristic.plan(frames, image)
            planner_name = "heuristic"
        if placement is None:
            raise RuntimeError("could not determine a placement")

        # 3. Track the box across frames.
        boxes = _track_box(frames, (placement.x, placement.y, placement.w, placement.h))
        end = placement.end_frame or len(frames)

        # 4. Composite the image into every frame in the window.
        for i in range(len(frames)):
            if placement.start_frame <= i < end:
                frames[i] = _composite(frames[i], image, boxes[i])

        # 5. Cut redundant segments.
        cuts: list[CutRange] = []
        if cut:
            cuts = _detect_cuts(frames, fps)
            frames = _apply_cuts(frames, cuts)

        # 6. Export.
        output_path = _export(
            frames, fps, output_path, audio_path=audio_path, ffmpeg_binary=ffmpeg_binary
        )
        if auto_audio is not None:
            try:
                auto_audio.unlink(missing_ok=True)
            except OSError:
                pass
        return EditReport(
            source_frames=len(frames) + sum(c.end - c.start for c in cuts),
            output_frames=len(frames),
            fps=fps,
            placement=placement,
            cuts=cuts,
            planner=planner_name,
            output_path=str(output_path),
        )


def _apply_cuts(frames: list[np.ndarray], cuts: list[CutRange]) -> list[np.ndarray]:
    """Remove the frame ranges listed in ``cuts``."""
    if not cuts:
        return frames
    keep = np.ones(len(frames), dtype=bool)
    for cut in cuts:
        keep[max(0, cut.start) : min(len(frames), cut.end)] = False
    return [f for f, k in zip(frames, keep, strict=False) if k]


def extract_audio(video_path: Path, out: Path) -> Path | None:
    """Extract the audio track of a video to a temp file, if it has one."""
    proc = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a",
            "-show_entries",
            "stream=index",
            "-of",
            "csv",
            str(video_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(video_path), "-vn", "-c:a", "aac", str(out)],
        capture_output=True,
        text=True,
        check=False,
    )
    return out if out.is_file() and out.stat().st_size > 0 else None


def _demo_vision_planner(
    frames: list[np.ndarray], image: np.ndarray
) -> Placement | None:
    """A stand-in vision planner: place in the upper-right quadrant.

    This demonstrates the ``VisionPlanner`` seam. A real vision model would
    describe the scene and return a richer placement; this keeps the pipeline
    testable offline.
    """
    if not frames:
        return None
    h, w = frames[0].shape[:2]
    img_h, img_w = image.shape[:2]
    box_w = int(w * _IMAGE_SCALE)
    box_h = int(box_w * img_h / max(1, img_w))
    return Placement(
        x=w - box_w - int(w * 0.03),
        y=int(h * 0.05),
        w=box_w,
        h=box_h,
        reason="vision demo: upper-right quadrant",
    )


def build_editor(vision: Any | None = None, **kwargs: Any) -> AiVideoEditor:
    """Build an editor, wiring a vision planner when one is available."""
    return AiVideoEditor(vision=vision, **kwargs)
