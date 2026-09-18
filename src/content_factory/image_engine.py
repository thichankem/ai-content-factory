"""Photo engine — Photoshop/CapCut-style raster image editing, pure stdlib+PIL.

Operates on real pixel data: crop, resize, rotate, flip, tone (brightness/
contrast/saturation), color balance, curves (shadow/mid/highlight), filters
(LUT-style presets), vignette, sharpen/blur, text overlays, background
removal (chroma-key + luminance), auto-enhance (histogram stretch + auto
contrast), and format export. Every op is a pure function over bytes so it
is trivially testable and callable from the agent tools registry.
"""

from __future__ import annotations

import base64
import binascii
import io
import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from PIL import (
    Image,
    ImageDraw,
    ImageEnhance,
    ImageFilter,
    ImageFont,
    ImageOps,
    ImageStat,
)

__all__ = [
    "ImageError",
    "ImageOp",
    "apply_ops",
    "auto_enhance",
    "export_bytes",
    "remove_background",
]


class ImageError(ValueError):
    """Raised when an image op is malformed or cannot be applied."""


_MAX_DIM = 8192
_MAX_OPS = 64


@dataclass(frozen=True)
class ImageOp:
    """One named operation with keyword parameters."""

    name: str
    params: dict[str, Any]

    def num(self, key: str, default: float) -> float:
        try:
            return float(self.params.get(key, default))
        except (TypeError, ValueError) as exc:
            raise ImageError(f"Op '{self.name}': '{key}' must be a number.") from exc

    def flag(self, key: str, default: bool) -> bool:
        return bool(self.params.get(key, default))


def load_image(data: bytes) -> Image.Image:
    """Decode image bytes into an RGBA PIL image, clamped to a sane size."""
    if not data:
        raise ImageError("Empty image payload.")
    try:
        img: Image.Image = Image.open(io.BytesIO(data))
        img.load()
    except Exception as exc:
        raise ImageError(f"Cannot decode image: {exc}") from exc
    if img.width > _MAX_DIM or img.height > _MAX_DIM:
        scale = min(_MAX_DIM / img.width, _MAX_DIM / img.height)
        img = img.resize(
            (int(img.width * scale), int(img.height * scale)),
            Image.Resampling.LANCZOS,
        )
    return img.convert("RGBA")


# --- Individual operations ---------------------------------------------------


def _op_resize(img: Image.Image, op: ImageOp) -> Image.Image:
    w = int(op.num("width", img.width))
    h = int(op.num("height", img.height))
    if w <= 0 or h <= 0:
        raise ImageError("resize: width/height must be positive.")
    fit = op.flag("fit", True)
    if fit:
        img = ImageOps.contain(img, (w, h), Image.Resampling.LANCZOS)
    return img.resize((min(w, _MAX_DIM), min(h, _MAX_DIM)), Image.Resampling.LANCZOS)


def _op_crop(img: Image.Image, op: ImageOp) -> Image.Image:
    left = int(op.num("left", 0))
    top = int(op.num("top", 0))
    width = int(op.num("width", img.width - left))
    height = int(op.num("height", img.height - top))
    if width <= 0 or height <= 0:
        raise ImageError("crop: width/height must be positive.")
    box = (
        max(0, left),
        max(0, top),
        min(img.width, left + width),
        min(img.height, top + height),
    )
    if box[2] - box[0] < 1 or box[3] - box[1] < 1:
        raise ImageError("crop: resulting box is empty.")
    return img.crop(box)


def _op_rotate(img: Image.Image, op: ImageOp) -> Image.Image:
    degrees = op.num("degrees", 0.0)
    expand = op.flag("expand", True)
    fill = (0, 0, 0, 0)
    return img.rotate(
        -degrees, resample=Image.Resampling.BICUBIC, expand=expand, fillcolor=fill
    )


def _op_flip(img: Image.Image, op: ImageOp) -> Image.Image:
    if op.flag("horizontal", True):
        return ImageOps.mirror(img)
    return ImageOps.flip(img)


def _op_tone(img: Image.Image, op: ImageOp) -> Image.Image:
    out = img
    if (b := op.num("brightness", 1.0)) != 1.0:
        out = ImageEnhance.Brightness(out).enhance(max(0.0, min(3.0, b)))
    if (c := op.num("contrast", 1.0)) != 1.0:
        out = ImageEnhance.Contrast(out).enhance(max(0.0, min(3.0, c)))
    if (s := op.num("saturation", 1.0)) != 1.0:
        out = ImageEnhance.Color(out).enhance(max(0.0, min(3.0, s)))
    return out


def _op_curves(img: Image.Image, op: ImageOp) -> Image.Image:
    """Shadow/mid/highlight lifts (like the Photoshop Curves panel nodes)."""
    shadows = op.num("shadows", 0.0)
    mids = op.num("mids", 0.0)
    highs = op.num("highlights", 0.0)
    if shadows == mids == highs == 0.0:
        return img
    rgb = img.convert("RGB")

    def curve(value: int) -> int:
        x = value / 255.0
        if x < 0.5:
            shift = shadows * (1.0 - 2.0 * x)
        else:
            shift = highs * (2.0 * x - 1.0)
        shift += mids * math.sin(math.pi * x) * 0.5
        return max(0, min(255, round(value + shift * 255.0)))

    lut = [curve(v) for v in range(256)]
    return rgb.point(lut * 3).convert("RGBA")


def _op_color_balance(img: Image.Image, op: ImageOp) -> Image.Image:
    r_shift = op.num("red", 0.0)
    g_shift = op.num("green", 0.0)
    b_shift = op.num("blue", 0.0)
    if r_shift == g_shift == b_shift == 0.0:
        return img
    rgb = img.convert("RGB")

    def channel(shift: float) -> Callable[[int], int]:
        def go(value: int) -> int:
            return max(0, min(255, round(value + shift * 120.0)))

        return go

    r, g, b = rgb.split()
    r = r.point(channel(r_shift))
    g = g.point(channel(g_shift))
    b = b.point(channel(b_shift))
    return Image.merge("RGB", (r, g, b)).convert("RGBA")


#: LUT-style filter presets: (r_scale, g_scale, b_scale, brightness, saturation)
_FILTERS: dict[str, tuple[float, float, float, float, float]] = {
    "grayscale": (1, 1, 1, 1.0, 0.0),
    "sepia": (1.05, 0.9, 0.7, 1.0, 0.6),
    "noir": (0.9, 0.9, 1.05, 1.05, 0.15),
    "vintage": (1.08, 1.0, 0.85, 1.05, 0.8),
    "cool": (0.92, 0.98, 1.12, 1.0, 1.05),
    "warm": (1.12, 1.02, 0.88, 1.02, 1.05),
    "vivid": (1.05, 1.05, 1.05, 1.05, 1.5),
    "fade": (1.0, 1.0, 1.0, 1.1, 0.7),
}


def _op_filter(img: Image.Image, op: ImageOp) -> Image.Image:
    name = str(op.params.get("preset", "")).lower()
    if name == "none" or not name:
        return img
    if name == "grayscale":
        return ImageOps.grayscale(img).convert("RGBA")
    preset = _FILTERS.get(name)
    if preset is None:
        raise ImageError(f"filter: unknown preset '{name}'. Known: {sorted(_FILTERS)}")
    rs, gs, bs, bright, sat = preset
    rgb = img.convert("RGB")
    r, g, b = rgb.split()

    r_tab = [max(0, min(255, round(i * rs))) for i in range(256)]
    g_tab = [max(0, min(255, round(i * gs))) for i in range(256)]
    b_tab = [max(0, min(255, round(i * bs))) for i in range(256)]
    r, g, b = r.point(r_tab), g.point(g_tab), b.point(b_tab)
    out = Image.merge("RGB", (r, g, b))
    out = ImageEnhance.Color(out).enhance(sat)
    out = ImageEnhance.Brightness(out).enhance(bright)
    return out.convert("RGBA")


def _op_vignette(img: Image.Image, op: ImageOp) -> Image.Image:
    strength = max(0.0, min(1.0, op.num("strength", 0.4)))
    if strength <= 0:
        return img
    mask = Image.new("L", (img.width, img.height), 0)
    draw = ImageDraw.Draw(mask)
    cx, cy = img.width // 2, img.height // 2
    max_r = math.hypot(cx, cy)
    steps = 32
    for i in range(steps, 0, -1):
        radius = max_r * i / steps
        alpha = int(255 * strength * (1 - i / steps) ** 2)
        draw.ellipse(
            (cx - radius, cy - radius, cx + radius, cy + radius),
            fill=255 - alpha,
        )
    black = Image.new("RGBA", img.size, (0, 0, 0, 255))
    return Image.composite(img, black, mask)


def _op_blur(img: Image.Image, op: ImageOp) -> Image.Image:
    radius = max(0.0, op.num("radius", 2.0))
    return img.filter(ImageFilter.GaussianBlur(radius)) if radius > 0 else img


def _op_sharpen(img: Image.Image, op: ImageOp) -> Image.Image:
    percent = max(0.0, min(500.0, op.num("percent", 50.0)))
    return ImageEnhance.Sharpness(img).enhance(1.0 + percent / 100.0)


def _op_text(img: Image.Image, op: ImageOp) -> Image.Image:
    """Draw text like the Type tool: size, color, position, stroke."""
    content = str(op.params.get("text", ""))
    if not content:
        return img
    size = int(max(8, min(400, op.num("size", 64))))
    color = str(op.params.get("color", "#ffffff"))
    stroke_width = int(max(0, op.num("stroke_width", 2)))
    stroke_color = str(op.params.get("stroke_color", "#000000"))
    position = str(op.params.get("position", "center"))
    font: Any
    try:
        font = ImageFont.truetype("arial.ttf", size)
    except Exception:  # noqa: BLE001 - font availability varies by OS
        font = ImageFont.load_default()
    draw = ImageDraw.Draw(img)
    bbox = draw.textbbox((0, 0), content, font=font, stroke_width=stroke_width)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    margin = int(size * 0.5)
    anchors = {
        "top-left": (margin, margin),
        "top-right": (img.width - text_w - margin, margin),
        "center": ((img.width - text_w) // 2, (img.height - text_h) // 2),
        "bottom-left": (margin, img.height - text_h - margin),
        "bottom-right": (img.width - text_w - margin, img.height - text_h - margin),
    }
    xy = anchors.get(position, anchors["center"])
    draw.text(
        xy,
        content,
        font=font,
        fill=color,
        stroke_width=stroke_width,
        stroke_fill=stroke_color,
    )
    return img


def _op_padding(img: Image.Image, op: ImageOp) -> Image.Image:
    """Letterbox to an exact canvas (aspect-ratio fit for a given platform)."""
    w = int(op.num("width", img.width))
    h = int(op.num("height", img.height))
    if w <= 0 or h <= 0:
        raise ImageError("padding: width/height must be positive.")
    color = str(op.params.get("color", "#000000"))
    hex_val = color.lstrip("#")
    if len(hex_val) == 6:
        rgb = tuple(int(hex_val[i : i + 2], 16) for i in (0, 2, 4))
    else:
        rgb = (0, 0, 0)
    contained = ImageOps.contain(img, (w, h), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (min(w, _MAX_DIM), min(h, _MAX_DIM)), (*rgb, 255))
    ox = (canvas.width - contained.width) // 2
    oy = (canvas.height - contained.height) // 2
    canvas.alpha_composite(contained, (ox, oy))
    return canvas


def _op_inpaint(img: Image.Image, op: ImageOp) -> Image.Image:
    method = op.params.get("method", "telea")
    if method not in ("telea", "navier-stokes"):
        raise ImageError("inpaint: method must be telea or navier-stokes.")
    radius = op.num("radius", 3.0)
    if not math.isfinite(radius) or not 1 <= radius <= 50:
        raise ImageError("inpaint: radius must be between 1 and 50.")
    encoded = op.params.get("mask_b64")
    if not isinstance(encoded, str) or not encoded:
        raise ImageError("inpaint: mask_b64 must contain a base64 image.")
    try:
        data = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ImageError("inpaint: mask_b64 must contain valid base64.") from exc
    try:
        with Image.open(io.BytesIO(data)) as source:
            if source.size != img.size:
                raise ImageError(
                    "inpaint: mask dimensions must match the current image."
                )
            mask = source.convert("L")
    except ImageError:
        raise
    except Exception as exc:
        raise ImageError("inpaint: cannot decode mask image.") from exc
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise ImageError("inpaint requires OpenCV and NumPy.") from exc
    selection = np.where(np.asarray(mask) > 127, 255, 0).astype(np.uint8)
    if not selection.any():
        return img.copy()
    if selection.all():
        raise ImageError("inpaint: mask must leave some source pixels unselected.")
    algorithm = cv2.INPAINT_TELEA if method == "telea" else cv2.INPAINT_NS
    pixels = np.asarray(img.convert("RGB"))
    filled = cv2.inpaint(pixels, selection, radius, algorithm)
    out = Image.fromarray(filled).convert("RGBA")
    out.putalpha(img.getchannel("A"))
    return out


_OPS: dict[str, Any] = {
    "resize": _op_resize,
    "crop": _op_crop,
    "rotate": _op_rotate,
    "flip": _op_flip,
    "tone": _op_tone,
    "curves": _op_curves,
    "color_balance": _op_color_balance,
    "filter": _op_filter,
    "vignette": _op_vignette,
    "blur": _op_blur,
    "sharpen": _op_sharpen,
    "text": _op_text,
    "padding": _op_padding,
    "inpaint": _op_inpaint,
}

#: Extended toolbox (light, colour, detail, local, retouch, transform, effects)
#: lives in :mod:`content_factory.photo_ops` and is merged into the same
#: dispatcher so every op flows through :func:`apply_ops` identically.
from . import photo_ops  # noqa: E402  (registered after the core registry)

_OPS.update(photo_ops.PHOTO_OPS)

#: Public list used by the agent tools manifest for discoverability.
KNOWN_OPS = sorted(_OPS)
KNOWN_FILTERS = sorted(_FILTERS)


# --- Compound operations ------------------------------------------------------


def auto_enhance(img: Image.Image) -> Image.Image:
    """One-click enhance: autocontrast + color balance + mild sharpen."""
    rgb = img.convert("RGB")
    gray = ImageOps.grayscale(rgb)
    stat = ImageStat.Stat(gray)
    cut_low = max(0, int(stat.mean[0] - 2.0 * max(4.0, stat.stddev[0] * 0.3)))
    cut_high = min(255, int(stat.mean[0] + 2.5 * max(4.0, stat.stddev[0] * 0.3)))
    rgb = ImageOps.autocontrast(rgb, cutoff=(cut_low, 255 - cut_high))
    rgb = ImageEnhance.Color(rgb).enhance(1.15)
    rgb = ImageEnhance.Sharpness(rgb).enhance(1.25)
    return rgb.convert("RGBA")


def remove_background(img: Image.Image, op: ImageOp) -> Image.Image:
    """Chroma-key / luminance background removal (green-screen style).

    ``color`` may be a hex color, or ``auto`` to key out the border average.
    ``tolerance`` (0..1) controls how far from the key color pixels remain.
    """
    tolerance = max(0.01, min(1.0, op.num("tolerance", 0.25)))
    key_name = str(op.params.get("color", "auto")).lower()
    rgb = img.convert("RGB")
    if key_name == "auto":
        w, h = rgb.size
        corners = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
        pixels: list[tuple[int, int, int]] = []
        for xy in corners:
            px = rgb.getpixel(xy)
            if isinstance(px, tuple) and len(px) >= 3:
                pixels.append((int(px[0]), int(px[1]), int(px[2])))
        if pixels:
            kr = sum(p[0] for p in pixels) / len(pixels)
            kg = sum(p[1] for p in pixels) / len(pixels)
            kb = sum(p[2] for p in pixels) / len(pixels)
        else:
            kr = kg = kb = 0.0
    else:
        hex_val = key_name.lstrip("#")
        if len(hex_val) != 6:
            raise ImageError("remove_background: color must be hex or 'auto'.")
        kr, kg, kb = (int(hex_val[i : i + 2], 16) for i in (0, 2, 4))
    rgba = img.copy()
    pix: Any = rgba.load()
    limit = tolerance * 441.67  # max distance in RGB space
    for y in range(rgba.height):
        for x in range(rgba.width):
            r, g, b, _a = pix[x, y]
            dist = math.sqrt((r - kr) ** 2 + (g - kg) ** 2 + (b - kb) ** 2)
            if dist < limit:
                pix[x, y] = (r, g, b, 0)
    return rgba


# --- Pipeline ------------------------------------------------------------------


def apply_ops(data: bytes, ops: list[dict[str, Any]]) -> Image.Image:
    """Decode, apply a sequence of named ops, return the final image."""
    img = load_image(data)
    if len(ops) > _MAX_OPS:
        raise ImageError(f"Too many ops ({len(ops)}); max is {_MAX_OPS}.")
    for entry in ops:
        if not isinstance(entry, dict) or "name" not in entry:
            raise ImageError("Every op must be an object with a 'name'.")
        op = ImageOp(name=str(entry["name"]), params=dict(entry.get("params", {})))
        if op.name == "auto_enhance":
            img = auto_enhance(img)
        elif op.name == "remove_background":
            img = remove_background(img, op)
        elif op.name in _OPS:
            img = _OPS[op.name](img, op)
        else:
            known = [*KNOWN_OPS, "auto_enhance", "remove_background"]
            raise ImageError(f"Unknown op '{op.name}'. Known: {known}")
    return img


def export_bytes(img: Image.Image, fmt: str = "png", quality: int = 90) -> bytes:
    """Serialize the final image (png/jpeg/webp)."""
    fmt = fmt.lower().lstrip(".")
    if fmt not in ("png", "jpeg", "jpg", "webp"):
        raise ImageError(f"Unsupported export format '{fmt}'. Use png/jpeg/webp.")
    buf = io.BytesIO()
    if fmt in ("jpeg", "jpg"):
        img.convert("RGB").save(buf, format="JPEG", quality=max(1, min(100, quality)))
    elif fmt == "webp":
        img.save(buf, format="WEBP", quality=max(1, min(100, quality)))
    else:
        img.save(buf, format="PNG")
    return buf.getvalue()
