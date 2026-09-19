"""Shared pixel maths for the image, video and compositing engines.

Three modules carried byte-identical copies of the same helpers — the Rec.709
luminance, the bilinear remap with its OpenCV/nearest-neighbour fallback, the
float→uint8 conversion, and the alpha-preserving array→image conversion. The
copies had already begun to drift: ``video_effects`` validated its input while
``photo_ops`` additionally guarded on NumPy being importable. They now share one
implementation per concern, and each caller asks for the guard it needs.

Every function here works on float RGB arrays in [0, 1] unless its name says
otherwise, because that is the space all three engines reason in.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from PIL import Image

__all__ = [
    "PixelError",
    "as_rgb",
    "luminance",
    "remap",
    "rgb_array",
    "to_image",
    "to_uint8",
]


class PixelError(ValueError):
    """Raised when an array is not a usable frame or RGB image."""


def _cv2() -> Any:
    """OpenCV when it is installed, else ``None`` (the documented fallback)."""
    try:
        import cv2
    except ImportError:  # pragma: no cover - optional heavy dependency
        return None
    return cv2


def as_rgb(frame: Any, *, error: type[Exception] = PixelError) -> np.ndarray:
    """Normalise a uint8 HxWx3 frame to float RGB in [0, 1]."""
    arr = np.asarray(frame, dtype=np.float32)
    if arr.ndim != 3 or arr.shape[2] < 3:
        raise error("A frame must be a HxWx3 array.")
    return arr[..., :3] / 255.0


def rgb_array(image: Image.Image) -> np.ndarray:
    """A PIL image as a float RGB array in [0, 1]."""
    return np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0


def to_uint8(rgb: np.ndarray) -> np.ndarray:
    """A float RGB array in [0, 1] as uint8."""
    return (np.clip(rgb, 0.0, 1.0) * 255.0).astype(np.uint8)


def to_image(rgb: np.ndarray, alpha_from: Image.Image | None = None) -> Image.Image:
    """A float RGB array as an RGBA image.

    When ``alpha_from`` is given its alpha channel is carried across: the photo
    operations work in RGB and must not silently flatten a transparent source.
    """
    out = Image.fromarray(to_uint8(rgb)).convert("RGBA")
    if alpha_from is not None:
        out.putalpha(alpha_from.getchannel("A"))
    return out


def luminance(rgb: np.ndarray) -> np.ndarray:
    """Rec.709 luminance of a float RGB array."""
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]


def remap(src: np.ndarray, map_x: np.ndarray, map_y: np.ndarray) -> np.ndarray:
    """Bilinear remap of a uint8 HxWxC array (OpenCV, else nearest-neighbour).

    The nearest-neighbour fallback exists so lens correction, perspective and
    the blur effects still run on a machine without OpenCV — coarser, never
    absent.
    """
    cv2 = _cv2()
    if cv2 is not None:
        return np.asarray(
            cv2.remap(
                src,
                map_x.astype(np.float32),
                map_y.astype(np.float32),
                cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_REPLICATE,
            )
        )
    ix = np.clip(np.round(map_x).astype(int), 0, src.shape[1] - 1)
    iy = np.clip(np.round(map_y).astype(int), 0, src.shape[0] - 1)
    return np.asarray(src[iy, ix])
