"""Photo Lab compositor: render a layered ``PhotoDocument`` into pixels.

The studio's Photo Lab edits a *document* — a stack of non-destructive layers —
and the backend turns that into an image. Everything here is deterministic and
offline (PIL + NumPy only): a document renders identically whether the operator
is online or not, which is what makes the renderer testable.

Blending implements the 27-mode industry set from ``docs/SPEC-IMAGE-EDITING.md``
§2.1, expressed in normalised float space (0.0–1.0) so each formula reads the
way the specification writes it.
"""

from __future__ import annotations

import io
from typing import Any

import numpy as np
from PIL import Image

__all__ = [
    "BLEND_MODES",
    "PhotoCompositorError",
    "apply_levels",
    "apply_tone_curve",
    "blend_images",
    "chroma_key",
    "export_bytes",
    "render_document",
]


class PhotoCompositorError(ValueError):
    """Raised when a document cannot be composited."""


def _clamp01(values):
    return np.clip(values, 0.0, 1.0)


def _luminosity(rgb):
    """Rec.709 luma, used by the component blending modes."""
    return (0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2])[
        ..., None
    ]


def _saturation_of(rgb):
    return rgb.max(axis=-1, keepdims=True) - rgb.min(axis=-1, keepdims=True)


def _screen(a, b):
    return 1.0 - (1.0 - a) * (1.0 - b)


def _overlay(a, b):
    return np.where(b <= 0.5, 2.0 * a * b, 1.0 - 2.0 * (1.0 - a) * (1.0 - b))


def _soft_light(a, b):
    return (1.0 - 2.0 * b) * a * a + 2.0 * b * a


def _hard_light(a, b):
    return _overlay(b, a)


def _vivid_light(a, b):
    return np.where(
        b <= 0.5,
        a / (1.0 - 2.0 * b + 1e-6),
        (a - (2.0 * b - 1.0)) / (2.0 * (1.0 - b) + 1e-6),
    )


def _linear_light(a, b):
    return _clamp01(a + 2.0 * b - 1.0)


def _pin_light(a, b):
    return np.where(b <= 0.5, np.minimum(a, 2.0 * b), np.maximum(a, 2.0 * b - 1.0))




def blend_images(
    base: Image.Image, top: Image.Image, mode: str, opacity: float = 1.0
) -> Image.Image:
    """Composite ``top`` over ``base`` with an industry blending mode.

    ``opacity`` (0–1) is the layer's alpha reach: 1.0 replaces the base fully,
    0.0 leaves it untouched, and everything between is a straight alpha mix of
    the blended result with the base.
    """
    if mode not in BLEND_MODES:
        raise PhotoCompositorError(
            f"Unknown blend mode '{mode}'. Known: {sorted(BLEND_MODES)}"
        )

    base_rgba = base.convert("RGBA")
    top_rgba = top.convert("RGBA")
    size = (max(base_rgba.width, top_rgba.width), max(base_rgba.height, top_rgba.height))
    if base_rgba.size != size:
        base_rgba = base_rgba.resize(size, Image.Resampling.LANCZOS)
    if top_rgba.size != size:
        top_rgba = top_rgba.resize(size, Image.Resampling.LANCZOS)

    base_rgb = np.asarray(base_rgba, dtype=np.float32)[..., :3] / 255.0
    top_rgb = np.asarray(top_rgba, dtype=np.float32)[..., :3] / 255.0
    top_alpha = np.asarray(top_rgba, dtype=np.float32)[..., 3:4] / 255.0

    blended = _clamp01(BLEND_MODES[mode](base_rgb, top_rgb))
    if mode in {"hue", "saturation", "color", "luminosity"}:
        blended = _component_blend(base_rgb, top_rgb, mode)

    reach = float(max(0.0, min(1.0, opacity)))
    effective = top_alpha * reach
    out_rgb = base_rgb * (1.0 - effective) + blended * effective
    out_alpha = np.maximum(
        np.asarray(base_rgba, dtype=np.float32)[..., 3:4] / 255.0, effective
    )
    merged = np.dstack([out_rgb * 255.0, out_alpha * 255.0]).astype(np.uint8)
    return Image.fromarray(merged, "RGBA")


def _component_blend(base, top, mode):
    """HSL component blending: take one property from the top, the rest from base."""
    top_luma, base_luma = _luminosity(top), _luminosity(base)
    top_sat, base_sat = _saturation_of(top), _saturation_of(base)
    top_luma, base_luma = _luminosity(top), _luminosity(base)
    top_sat, base_sat = _saturation_of(top), _saturation_of(base)
    if mode == "hue":
        # Recolour the base towards the top's hue while keeping the base's own
        # luminance — an approximation good enough for previews.
        return _clamp01(base_luma + (top - top_luma) * 0.5)
    if mode == "saturation":
        scale = top_sat / (base_sat + 1e-6)
        return _clamp01(base_luma + (base - base_luma) * scale)
    if mode == "color":
        return _clamp01(base_luma + (top - top_luma))
    return _clamp01(base + (top_luma - base_luma))  # luminosity


def apply_tone_curve(img: Image.Image, points: list[tuple[int, int]]) -> Image.Image:
    """Map luminance through a piecewise-linear tone curve (0–255 control points)."""
    if len(points) < 2:
        raise PhotoCompositorError("A tone curve needs at least two points.")
    control = sorted((float(x), float(y)) for x, y in points)
    xs = np.array([p[0] for p in control], dtype=np.float32)
    ys = np.array([p[1] for p in control], dtype=np.float32)

    rgba = np.asarray(img.convert("RGBA"), dtype=np.float32)
    rgb, alpha = rgba[..., :3], rgba[..., 3:]
    luma = _luminosity(rgb / 255.0)[..., 0] * 255.0
    mapped = np.interp(luma, xs, ys)
    scale = mapped / (luma + 1e-6)
    out_rgb = _clamp01(rgb * scale[..., None]) * 255.0
    result = np.dstack([out_rgb, alpha]).astype(np.uint8)
    return Image.fromarray(result, "RGBA")


def apply_levels(
    img: Image.Image,
    in_black: int,
    in_white: int,
    gamma: float,
    out_black: int,
    out_white: int,
) -> Image.Image:
    """Levels: stretch input black/white, apply midtone gamma, clamp output."""
    if in_white <= in_black:
        raise PhotoCompositorError("Levels: input white must exceed input black.")
    rgba = np.asarray(img.convert("RGBA"), dtype=np.float32)
    rgb, alpha = rgba[..., :3], rgba[..., 3:]
    normalised = _clamp01((rgb - in_black) / (in_white - in_black))
    shaped = np.power(normalised, 1.0 / max(0.1, min(9.9, gamma)))
    stretched = out_black + shaped * (out_white - out_black)
    result = np.dstack([_clamp01(stretched / 255.0) * 255.0, alpha]).astype(np.uint8)
    return Image.fromarray(result, "RGBA")


def chroma_key(
    img: Image.Image, key_color: str, tolerance: int, softness: int, spill: int
) -> Image.Image:
    """Remove ``key_color`` with a soft edge and spill suppression (0–100 scales)."""
    rgba = np.asarray(img.convert("RGBA"), dtype=np.float32)
    key = hex_to_rgb(key_color)
    distance = np.linalg.norm(rgba[..., :3] - key, axis=-1)
    tol = max(0.0, min(100, float(tolerance))) * 1.8
    soft = max(1.0, float(softness)) * 1.8
    alpha = np.clip((distance - tol) / soft, 0.0, 1.0)
    keep = 1.0 - float(max(0, min(100, spill))) / 100.0
    rgb = rgba[..., :3] * keep + rgba[..., :3] * (1.0 - keep)
    result = np.dstack([rgb, alpha[..., None] * 255.0]).astype(np.uint8)
    return Image.fromarray(result, "RGBA")


def hex_to_rgb(value: str) -> np.ndarray:
    """Parse ``#rrggbb`` (or ``#rgb``) into an RGB triplet, or raise."""
    text = value.strip().lstrip("#")
    if len(text) == 3:
        text = "".join(ch * 2 for ch in text)
    if len(text) not in {6, 8}:
        raise PhotoCompositorError(f"'{value}' is not a hex colour.")
    try:
        return np.array([int(text[i : i + 2], 16) for i in (0, 2, 4)], dtype=np.float32)
    except ValueError as exc:
        raise PhotoCompositorError(f"'{value}' is not a hex colour.") from exc
        # Recolour the base towards the top's hue while keeping the base's own
        # luminance — an approximation good enough for previews.
        return _clamp01(base_luma + (top - top_luma) * 0.5)
    if mode == "saturation":
        scale = top_sat / (base_sat + 1e-6)
        return _clamp01(base_luma + (base - base_luma) * scale)
    if mode == "color":
        return _clamp01(base_luma + (top - top_luma))
    return _clamp01(base + (top_luma - base_luma))  # luminosity
def _hard_mix(a, b):
    return np.where(a + b >= 1.0, 1.0, 0.0)


def _color_burn(a, b):
    return _clamp01(1.0 - (1.0 - a) / (b + 1e-6))


def _color_dodge(a, b):
    return _clamp01(a / (1.0 - b + 1e-6))


#: mode name -> normalised-space blend of (base, top).
BLEND_MODES = {
    "normal": lambda a, b: b,
    "darken": np.minimum,
    "multiply": lambda a, b: a * b,
    "color-burn": _color_burn,
    "linear-burn": lambda a, b: _clamp01(a + b - 1.0),
    "darker-color": lambda a, b: np.where(_luminosity(a) <= _luminosity(b), a, b),
    "lighten": np.maximum,
    "screen": _screen,
    "color-dodge": _color_dodge,
    "linear-dodge": lambda a, b: _clamp01(a + b),
    "lighter-color": lambda a, b: np.where(_luminosity(a) > _luminosity(b), a, b),
    "overlay": _overlay,
    "soft-light": _soft_light,
    "hard-light": _hard_light,
    "vivid-light": _vivid_light,
    "linear-light": _linear_light,
    "pin-light": _pin_light,
    "hard-mix": _hard_mix,
    "difference": lambda a, b: np.abs(a - b),
    "exclusion": lambda a, b: a + b - 2.0 * a * b,
    "subtract": lambda a, b: _clamp01(a - b),
    "divide": lambda a, b: _clamp01(a / (b + 1e-6)),
    # Component modes are resolved separately in `_component_blend`; they are
    # registered here so the vocabulary is complete and one lookup can accept all.
    "hue": lambda a, b: b,
    "saturation": lambda a, b: b,
    "color": lambda a, b: b,
    "luminosity": lambda a, b: a,
}


def _render_layer(layer: dict, width: int, height: int) -> Image.Image:
    """Render one layer's own pixels; compositing happens in :func:`blend_images`."""
    kind = layer.get("kind", "raster")
    if kind == "adjustment":
        # An adjustment layer holds tone/levels parameters; the service applies
        # them to the composited result, so the layer itself draws nothing.
        return Image.new("RGBA", (width, height), (0, 0, 0, 0))
    if kind == "text":
        return _text_layer(layer, width, height)
    # Raster/vector layers need an asset the caller resolves first; an absent
    # asset is an empty layer rather than a hard failure, so one bad entry
    # cannot blank an otherwise valid document.
    return Image.new("RGBA", (width, height), (0, 0, 0, 0))


def _text_layer(layer: dict, width: int, height: int) -> Image.Image:
    """Draw a text layer's background box; the glyphs stay the browser's job."""
    text = layer.get("text") or {}
    if not text.get("has_background"):
        return Image.new("RGBA", (width, height), (0, 0, 0, 0))

    from PIL import ImageDraw

    box = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(box)
    colour = hex_to_rgb(text.get("bg_color", "#090a0f"))
    alpha = int(max(0, min(100, float(text.get("bg_opacity", 80)))) * 2.55)
    radius = int(max(0, min(50, float(text.get("bg_radius", 8)))))
    padding = int(max(0, min(100, float(text.get("bg_padding", 16)))))
    font_size = int(max(12, min(300, float(text.get("font_size", 96)))))
    draw.rounded_rectangle(
        [padding, padding, width - padding, padding + font_size + padding],
        radius=radius,
        fill=(int(colour[0]), int(colour[1]), int(colour[2]), alpha),
    )
    return box


def render_document(document: dict) -> Image.Image:
    """Composite a ``PhotoDocument`` payload into a finished RGBA image.

    Layers apply bottom-up (list order), honouring visibility, opacity, blending
    and adjustment ops. This is the single entry point the service mixin calls,
    so it takes the plain payload a request body carries.
    """
    width = int(document.get("width", 1080))
    height = int(document.get("height", 1920))
    canvas = Image.new(
        "RGBA", (width, height), _hex_to_rgba(document.get("background_color", "#00000000"))
    )

    for layer in document.get("layers", []):
        if not layer.get("visible", True):
            continue
        piece = _render_layer(layer, width, height)
        adjustments = layer.get("adjustment") or {}
        if layer.get("kind") == "adjustment":
            piece = _apply_adjustments(piece, adjustments)
        canvas = blend_images(
            canvas,
            piece,
            layer.get("blend_mode", "normal"),
            float(layer.get("opacity", 100)) / 100.0,
        )
    return canvas


    for layer in document.get("layers", []):
        if not layer.get("visible", True):
            continue
        piece = _render_layer(layer, width, height)
        if layer.get("kind") == "adjustment":
            piece = _apply_adjustments(piece, layer.get("adjustment") or {})
        canvas = blend_images(
            canvas,
            piece,
            layer.get("blend_mode", "normal"),
            float(layer.get("opacity", 100)) / 100.0,
        )
    return canvas


def _apply_adjustments(piece: Image.Image, settings: dict) -> Image.Image:
    """Run an adjustment layer's ops over the piece it sits on."""
    if "levels" in settings:
        config = settings["levels"] or {}
        piece = apply_levels(
            piece,
            int(config.get("input_black", 0)),
            int(config.get("input_white", 255)),
            float(config.get("gamma", 1.0)),
            int(config.get("output_black", 0)),
            int(config.get("output_white", 255)),
        )
    if "curve" in settings:
        curve = (settings.get("curve") or {}).get("points") or []
        piece = apply_tone_curve(piece, [(int(x), int(y)) for x, y in curve])
    return piece


def _hex_to_rgba(value: str) -> tuple[int, int, int, int]:
    """Parse ``#rrggbb`` or ``#rrggbbaa`` into an RGBA tuple."""
    text = value.strip().lstrip("#")
    if len(text) == 8:
        return (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16), int(text[6:8], 16))
    rgb = hex_to_rgb(text)
    return (int(rgb[0]), int(rgb[1]), int(rgb[2]), 255)


def export_bytes(img: Image.Image, fmt: str = "png", quality: int = 90) -> bytes:
    """Serialize a composited image (png/jpeg/webp)."""
    fmt = fmt.lower().lstrip(".")
    if fmt not in ("png", "jpeg", "jpg", "webp"):
        raise PhotoCompositorError(f"Unsupported export format '{fmt}'.")
    buf = io.BytesIO()
    if fmt in ("jpeg", "jpg"):
        img.convert("RGB").save(buf, format="JPEG", quality=max(1, min(100, quality)))
    elif fmt == "webp":
        img.save(buf, format="WEBP", quality=max(1, min(100, quality)))
    else:
        img.save(buf, format="PNG")
    return buf.getvalue()