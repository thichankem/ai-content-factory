"""Video frame effects — pure NumPy, offline, vision-free.

Each effect is a pure ``(frame, params) -> frame`` function over a float RGB
array in [0, 1] (shape ``H x W x 3``). Because they touch real pixels but never
need a model, a text-only agent can apply a "glitch" or "film grain" look to any
frame, and a renderer can call them per-frame. Deterministic when a ``seed`` is
supplied, so a recipe reproduces exactly.

The module also exposes :func:`effect_catalog` — plain-language descriptions of
every effect and its parameters — which is what lets a non-vision agent (or a
screen reader) know what each effect does and how to tune it.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from .params import clamp01 as _clamp01
from .params import seed as _seed
from .pixels import as_rgb
from .pixels import luminance as _luminance
from .pixels import remap as _remap
from .pixels import to_uint8 as _to_uint8

__all__ = [
    "apply_frame_effect",
    "effect_catalog",
    "frame_effect_names",
]


class VideoEffectError(ValueError):
    """Raised when a frame effect is malformed or cannot be applied."""


# --- Individual effects ------------------------------------------------------


def _fx_glitch(rgb: np.ndarray, params: dict[str, Any]) -> np.ndarray:
    """RGB-channel offset + horizontal slice displacement."""
    amount = _clamp01(params.get("amount", 0.5))
    if amount <= 0:
        return rgb
    rng = np.random.default_rng(_seed(params))
    out = rgb.copy()
    h, w = rgb.shape[:2]
    shift = int(amount * w * 0.08)
    # Channel offset for chromatic glitch.
    out[..., 0] = np.roll(out[..., 0], rng.integers(-shift, shift + 1), axis=1)
    out[..., 2] = np.roll(out[..., 2], rng.integers(-shift, shift + 1), axis=1)
    # Displace a few horizontal bands.
    bands = max(1, int(amount * 6))
    for _ in range(bands):
        y = int(rng.integers(0, h))
        band_h = max(1, int(rng.integers(1, h // 8)))
        dx = int(rng.integers(-shift, shift + 1))
        out[y : y + band_h] = np.roll(out[y : y + band_h], dx, axis=1)
    return out


def _fx_shake(rgb: np.ndarray, params: dict[str, Any]) -> np.ndarray:
    """Camera shake: translate the frame by a small random offset."""
    amount = _clamp01(params.get("amount", 0.4))
    if amount <= 0:
        return rgb
    rng = np.random.default_rng(_seed(params))
    h, w = rgb.shape[:2]
    dx = int(rng.integers(-int(amount * w * 0.05), int(amount * w * 0.05) + 1))
    dy = int(rng.integers(-int(amount * h * 0.05), int(amount * h * 0.05) + 1))
    return np.roll(np.roll(rgb, dx, axis=1), dy, axis=0)


def _fx_distortion(rgb: np.ndarray, params: dict[str, Any]) -> np.ndarray:
    """Radial bulge/pinch around the centre."""
    strength = float(params.get("strength", 0.0))  # +bulge, -pinch
    if strength == 0:
        return rgb
    h, w = rgb.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = w / 2.0, h / 2.0
    nx = (xx - cx) / cx
    ny = (yy - cy) / cy
    dist = np.sqrt(nx**2 + ny**2)
    scale = 1.0 + strength * (1.0 - dist) * 0.5
    map_x = cx + (xx - cx) * scale
    map_y = cy + (yy - cy) * scale
    return _remap(_to_uint8(rgb), map_x, map_y).astype(np.float32) / 255.0


def _fx_glow(rgb: np.ndarray, params: dict[str, Any]) -> np.ndarray:
    """Bloom: blur the bright areas and add them back."""
    amount = _clamp01(params.get("amount", 0.5))
    if amount <= 0:
        return rgb
    try:
        from PIL import Image, ImageFilter

        pil = Image.fromarray(_to_uint8(rgb))
        blurred = pil.filter(ImageFilter.GaussianBlur(radius=max(1, int(amount * 12))))
        bloom = np.asarray(blurred, dtype=np.float32) / 255.0
    except Exception:  # noqa: BLE001 - fall back to a box blur approximation
        kernel = np.ones((5, 5, 1), dtype=np.float32) / 25.0
        padded = np.pad(rgb, ((2, 2), (2, 2), (0, 0)), mode="edge")
        bloom = np.zeros_like(rgb)
        for i in range(5):
            for j in range(5):
                bloom += (
                    padded[i : i + rgb.shape[0], j : j + rgb.shape[1]] * kernel[i, j]
                )
    bright = np.clip(_luminance(rgb) - 0.6, 0.0, 1.0)[..., None]
    return rgb + bloom * bright * amount


def _fx_film_grain(rgb: np.ndarray, params: dict[str, Any]) -> np.ndarray:
    """Monochrome film grain."""
    amount = _clamp01(params.get("amount", 0.2))
    if amount <= 0:
        return rgb
    rng = np.random.default_rng(_seed(params))
    noise = rng.normal(0.0, amount * 0.12, rgb.shape[:2])[..., None]
    return np.asarray(np.clip(rgb + noise, 0.0, 1.0), dtype=np.float32)


def _fx_motion_blur(rgb: np.ndarray, params: dict[str, Any]) -> np.ndarray:
    """Directional motion blur (rolling average)."""
    angle = float(params.get("angle", 0.0))
    distance = max(0.0, float(params.get("distance", 8.0)))
    if distance <= 0:
        return rgb
    rad = math.radians(angle)
    dx = math.cos(rad)
    dy = math.sin(rad)
    steps = max(2, int(distance))
    acc = np.zeros_like(rgb)
    for i in range(steps + 1):
        t = i / steps
        ox = round(dx * distance * (t - 0.5))
        oy = round(dy * distance * (t - 0.5))
        acc += np.roll(rgb, (oy, ox), axis=(0, 1))
    return acc / (steps + 1)


def _fx_particles(rgb: np.ndarray, params: dict[str, Any]) -> np.ndarray:
    """Sparkle/dust particles drifting across the frame."""
    count = max(0, int(params.get("count", 40)))
    if count <= 0:
        return rgb
    rng = np.random.default_rng(_seed(params))
    h, w = rgb.shape[:2]
    out = rgb.copy()
    xs = rng.integers(0, w, size=count)
    ys = rng.integers(0, h, size=count)
    radii = rng.uniform(0.5, 2.5, size=count)
    intensities = rng.uniform(0.3, 1.0, size=count)
    for x, y, r, intensity in zip(xs, ys, radii, intensities, strict=True):
        rr = max(1, int(r))
        x0, x1 = max(0, x - rr), min(w, x + rr + 1)
        y0, y1 = max(0, y - rr), min(h, y + rr + 1)
        out[y0:y1, x0:x1] = np.clip(out[y0:y1, x0:x1] + intensity * 0.6, 0.0, 1.0)
    return out


def _fx_chromatic_aberration(rgb: np.ndarray, params: dict[str, Any]) -> np.ndarray:
    """Offset the red and blue channels for a lens-aberration fringe."""
    amount = _clamp01(params.get("amount", 0.3))
    if amount <= 0:
        return rgb
    out = rgb.copy()
    shift = max(1, int(amount * 12))
    out[..., 0] = np.roll(out[..., 0], shift, axis=1)
    out[..., 2] = np.roll(out[..., 2], -shift, axis=1)
    return out


def _fx_pixelate(rgb: np.ndarray, params: dict[str, Any]) -> np.ndarray:
    """Downscale then upscale to a blocky mosaic."""
    block = max(1, int(params.get("block", 8)))
    h, w = rgb.shape[:2]
    if block <= 1:
        return rgb
    small = rgb[::block, ::block]
    small = np.repeat(np.repeat(small, block, axis=0), block, axis=1)
    return small[:h, :w]


def _fx_scanlines(rgb: np.ndarray, params: dict[str, Any]) -> np.ndarray:
    """CRT scanlines: darken alternating rows."""
    amount = _clamp01(params.get("amount", 0.4))
    if amount <= 0:
        return rgb
    out = rgb.copy()
    out[::2] *= 1.0 - amount * 0.5
    return out


def _fx_freeze(rgb: np.ndarray, params: dict[str, Any]) -> np.ndarray:
    """Hold the frame (freeze-frame). Identity transform."""
    return rgb


_EFFECTS: dict[str, Any] = {
    "glitch": _fx_glitch,
    "shake": _fx_shake,
    "distortion": _fx_distortion,
    "glow": _fx_glow,
    "film_grain": _fx_film_grain,
    "motion_blur": _fx_motion_blur,
    "particles": _fx_particles,
    "chromatic_aberration": _fx_chromatic_aberration,
    "pixelate": _fx_pixelate,
    "scanlines": _fx_scanlines,
    "freeze": _fx_freeze,
}


def frame_effect_names() -> list[str]:
    """Names of every available frame effect."""
    return sorted(_EFFECTS)


def apply_frame_effect(
    frame: Any, name: str, params: dict[str, Any] | None = None
) -> np.ndarray:
    """Apply one named effect to a frame (uint8 HxWx3 in, uint8 HxWx3 out)."""
    name = (name or "").lower()
    if name not in _EFFECTS:
        raise VideoEffectError(f"Unknown effect '{name}'. Known: {sorted(_EFFECTS)}")
    rgb = as_rgb(frame, error=VideoEffectError)
    out = _EFFECTS[name](rgb, dict(params or {}))
    return _to_uint8(out)


#: Plain-language docs for every effect, for the accessibility layer.
_EFFECT_DOCS: dict[str, dict[str, Any]] = {
    "glitch": {
        "description": "Digital glitch: shifts colour channels and displaces "
        "horizontal bands for a corrupted, techno look.",
        "params": {
            "amount": "0..1 strength.",
            "seed": "Random seed for reproducibility.",
        },
    },
    "shake": {
        "description": "Camera shake: jolts the frame by a small random offset, "
        "like handheld footage.",
        "params": {"amount": "0..1 how violent the shake is.", "seed": "Random seed."},
    },
    "distortion": {
        "description": "Radial distortion: bulges outward (positive) or pinches "
        "inward (negative) around the centre.",
        "params": {"strength": "Positive bulges, negative pinches."},
    },
    "glow": {
        "description": "Bloom/glow: blurs the bright areas and adds them back "
        "for a dreamy, luminous halo.",
        "params": {"amount": "0..1 how strong the bloom is."},
    },
    "film_grain": {
        "description": "Analog film grain: adds fine monochrome noise.",
        "params": {"amount": "0..1 how much grain.", "seed": "Random seed."},
    },
    "motion_blur": {
        "description": "Directional motion blur along an angle to suggest movement.",
        "params": {
            "angle": "Direction in degrees.",
            "distance": "How far the blur travels.",
        },
    },
    "particles": {
        "description": "Drifting sparkle/dust particles across the frame.",
        "params": {"count": "Number of particles.", "seed": "Random seed."},
    },
    "chromatic_aberration": {
        "description": "Lens fringe: offsets the red and blue channels for a "
        "colour-separated edge.",
        "params": {"amount": "0..1 how much the channels separate."},
    },
    "pixelate": {
        "description": "Mosaic pixelation: downsamples then upsamples to blocks.",
        "params": {"block": "Pixel block size (>=1)."},
    },
    "scanlines": {
        "description": "CRT scanlines: darkens alternating rows.",
        "params": {"amount": "0..1 how dark the lines are."},
    },
    "freeze": {
        "description": "Freeze frame: holds the current frame (identity).",
        "params": {},
    },
}


def effect_catalog() -> dict[str, Any]:
    """Every effect with a plain-language description and its parameters."""
    return {
        "effects": [
            {
                "name": name,
                **(_EFFECT_DOCS.get(name, {"description": name, "params": {}})),
            }
            for name in sorted(_EFFECTS)
        ]
    }
