"""Extended photo operations — the full Photoshop/Capture-One-style toolbox.

This module extends :mod:`content_factory.image_engine` with the operations the
operator asked for that the core engine did not yet ship: fine light controls
(exposure, highlights, shadows, whites/blacks, levels), colour (white balance,
temperature/tint, vibrance, HSL mixer, colour grade, split toning), detail
(noise reduction, clarity, texture, dehaze), local adjustments (radial /
gradient / brush masks), retouching (spot heal, clone stamp, red-eye, liquify,
dodge & burn, frequency separation), transforms (straighten, perspective, lens
correction) and effects (film grain, watermark, motion/lens blur).

Every op is a pure ``(image, op) -> image`` function over real pixels, using
only the standard library, Pillow and NumPy, so it runs offline everywhere.
Machine-learning dependent features (subject segmentation, panorama, HDR,
RAW, upscale) are deliberately *not* here — they are pluggable adapters wired
elsewhere, and their absence degrades gracefully.

Design note: this module intentionally does **not** import
:mod:`content_factory.image_engine` at module load (that would create an import
cycle, because ``image_engine`` imports this module to register the ops). Ops
duck-type the ``ImageOp`` object (``.num`` / ``.flag`` / ``.params``) and raise
:class:`~content_factory.image_engine.ImageError` through a deferred import.
"""

from __future__ import annotations

import math
from typing import Any, NoReturn

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

try:  # pragma: no cover - numpy is a hard dependency of the project
    import numpy as np
except ImportError:  # pragma: no cover
    np = None  # type: ignore[assignment]


def _fail(message: str) -> NoReturn:
    """Raise an :class:`ImageError` without a module-load import cycle."""
    from .image_engine import ImageError

    raise ImageError(message)


def _num(op: Any, key: str, default: float) -> float:
    try:
        return float(op.params.get(key, default))
    except (TypeError, ValueError):
        _fail(f"'{key}' must be a number.")


def _flag(op: Any, key: str, default: bool) -> bool:
    return bool(op.params.get(key, default))


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


# --- numpy helpers -----------------------------------------------------------


def _rgb(img: Image.Image) -> np.ndarray:
    """Image -> float RGB array in [0, 1]."""
    if np is None:
        _fail("NumPy is required for this operation.")
    return np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0


def _to_img(arr: np.ndarray, img: Image.Image) -> Image.Image:
    """Float RGB array in [0, 1] -> RGBA image preserving the original alpha."""
    out = Image.fromarray((np.clip(arr, 0.0, 1.0) * 255.0).astype(np.uint8), mode="RGB")
    out = out.convert("RGBA")
    out.putalpha(img.getchannel("A"))
    return out


def _luminance(rgb: np.ndarray) -> np.ndarray:
    """Rec.709 luminance of a float RGB array."""
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]


# --- Light -------------------------------------------------------------------


def _op_exposure(img: Image.Image, op: Any) -> Image.Image:
    ev = _num(op, "ev", 0.0)
    if ev == 0.0:
        return img
    rgb = _rgb(img)
    rgb = rgb * (2.0**ev)
    return _to_img(rgb, img)


def _op_highlights(img: Image.Image, op: Any) -> Image.Image:
    """Recover blown highlights: pull bright tones back toward mid."""
    amount = _num(op, "amount", 0.0)
    if amount == 0.0:
        return img
    rgb = _rgb(img)
    lum = _luminance(rgb)
    # Weight is highest near the top of the range, zero below ~0.5.
    weight = np.clip((lum - 0.5) / 0.5, 0.0, 1.0)[..., None]
    # Pull bright pixels downward proportional to their brightness.
    rgb = rgb - weight * (lum[..., None] - 0.5) * amount
    return _to_img(rgb, img)


def _op_shadows(img: Image.Image, op: Any) -> Image.Image:
    """Lift shadows: reveal detail in dark regions."""
    amount = _num(op, "amount", 0.0)
    if amount == 0.0:
        return img
    rgb = _rgb(img)
    lum = _luminance(rgb)
    weight = np.clip((0.5 - lum) / 0.5, 0.0, 1.0)[..., None]
    rgb = rgb + weight * (0.5 - lum[..., None]) * amount
    return _to_img(rgb, img)


def _op_whites(img: Image.Image, op: Any) -> Image.Image:
    """Adjust the absolute white point (clip or lift the top of the range)."""
    amount = _num(op, "amount", 0.0)  # -1..1; negative clips whites, positive lifts
    if amount == 0.0:
        return img
    rgb = _rgb(img)
    if amount > 0:
        # Lift everything above the midpoint toward white.
        rgb = rgb + (1.0 - rgb) * amount
    else:
        # Clip the top of the range down.
        floor = 1.0 + amount  # e.g. amount=-0.2 -> floor 0.8
        rgb = np.minimum(rgb, floor)
        rgb = rgb / max(floor, 1e-6)
    return _to_img(rgb, img)


def _op_blacks(img: Image.Image, op: Any) -> Image.Image:
    """Adjust the absolute black point."""
    amount = _num(op, "amount", 0.0)  # -1..1; negative clips blacks, positive lifts
    if amount == 0.0:
        return img
    rgb = _rgb(img)
    if amount < 0:
        ceil = -amount  # clip the bottom of the range to black
        rgb = np.maximum(rgb - ceil, 0.0) / max(1.0 - ceil, 1e-6)
    else:
        rgb = rgb * (1.0 - amount)
    return _to_img(rgb, img)


def _op_levels(img: Image.Image, op: Any) -> Image.Image:
    """Levels: black point, gamma and white point on the luminance range."""
    black = _clamp01(_num(op, "black", 0.0))
    white = _clamp01(_num(op, "white", 1.0))
    gamma = max(0.05, min(5.0, _num(op, "gamma", 1.0)))
    if black == 0.0 and white == 1.0 and gamma == 1.0:
        return img
    rgb = _rgb(img)
    span = max(white - black, 1e-6)
    norm = np.clip((rgb - black) / span, 0.0, 1.0)
    norm = np.power(norm, 1.0 / gamma)
    return _to_img(norm, img)


# --- Colour ------------------------------------------------------------------


def _op_white_balance(img: Image.Image, op: Any) -> Image.Image:
    """White balance: temperature (warm/cool) and tint (green/magenta)."""
    temperature = _num(op, "temperature", 0.0)  # -1..1, +warmer (more red/yellow)
    tint = _num(op, "tint", 0.0)  # -1..1, +more magenta
    if temperature == 0.0 and tint == 0.0:
        return img
    rgb = _rgb(img)
    # Temperature scales red vs blue inversely.
    r_gain = 1.0 + temperature * 0.15
    b_gain = 1.0 - temperature * 0.15
    # Tint shifts green vs magenta (red+blue).
    g_gain = 1.0 - tint * 0.15
    rb_gain = 1.0 + tint * 0.075
    rgb[..., 0] *= r_gain * rb_gain
    rgb[..., 1] *= g_gain
    rgb[..., 2] *= b_gain * rb_gain
    return _to_img(rgb, img)


def _op_temperature(img: Image.Image, op: Any) -> Image.Image:
    """Alias for the temperature axis of white balance."""
    return _op_white_balance(img, op)


def _op_tint(img: Image.Image, op: Any) -> Image.Image:
    """Alias for the tint axis of white balance."""
    return _op_white_balance(img, op)


def _op_vibrance(img: Image.Image, op: Any) -> Image.Image:
    """Boost muted colours while protecting already-saturated ones (and skin)."""
    amount = _num(op, "amount", 0.0)
    if amount == 0.0:
        return img
    rgb = _rgb(img)
    mx = rgb.max(axis=2, keepdims=True)
    mn = rgb.min(axis=2, keepdims=True)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0.0)
    # Muted colours get a stronger boost; saturated ones barely move.
    gain = 1.0 + amount * (1.0 - sat)
    gray = _luminance(rgb)[..., None]
    rgb = gray + (rgb - gray) * gain
    return _to_img(rgb, img)


#: HSL mixer channels and their approximate hue centres (0..360).
_HSL_CHANNELS: dict[str, float] = {
    "red": 0.0,
    "orange": 30.0,
    "yellow": 60.0,
    "green": 120.0,
    "cyan": 180.0,
    "blue": 240.0,
    "purple": 280.0,
    "magenta": 315.0,
}


def _op_hsl(img: Image.Image, op: Any) -> Image.Image:
    """Per-channel HSL mixer: hue shift, saturation and luminance per colour."""
    if np is None:
        _fail("NumPy is required for this operation.")
    rgb = _rgb(img)
    mx = rgb.max(axis=2)
    mn = rgb.min(axis=2)
    delta = mx - mn
    lum = (mx + mn) / 2.0
    # Hue in degrees (0..360); undefined (grey) handled by a mask.
    hue = np.zeros_like(mx)
    mask = delta > 1e-6
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    with np.errstate(invalid="ignore", divide="ignore"):
        hr = (((g - b) / delta) % 6.0) * 60.0
        hg = (((b - r) / delta) + 2.0) * 60.0
        hb = (((r - g) / delta) + 4.0) * 60.0
    hue = np.where(mask, np.select([mx == r, mx == g, mx == b], [hr, hg, hb]), 0.0)
    hue = (hue + 360.0) % 360.0

    sat = np.where(mask, delta / np.maximum(mx, 1e-6), 0.0)

    # Build per-channel influence weights (triangular falloff around centre).
    for name, centre in _HSL_CHANNELS.items():
        h_shift = _num(op, f"{name}_hue", 0.0)
        s_shift = _num(op, f"{name}_sat", 0.0)
        l_shift = _num(op, f"{name}_lum", 0.0)
        if h_shift == 0.0 and s_shift == 0.0 and l_shift == 0.0:
            continue
        angular = np.abs(((hue - centre + 180.0) % 360.0) - 180.0)
        influence = np.clip(1.0 - angular / 60.0, 0.0, 1.0)
        influence *= mask
        if h_shift:
            hue = (hue + influence * h_shift) % 360.0
        if s_shift:
            sat = np.clip(sat + influence * s_shift * 0.5, 0.0, 1.0)
        if l_shift:
            lum = np.clip(lum + influence * l_shift * 0.5, 0.0, 1.0)

    # Convert HSL back to RGB.
    c = (1.0 - np.abs(2.0 * lum - 1.0)) * sat
    hp = hue / 60.0
    x = c * (1.0 - np.abs(hp % 2.0 - 1.0))
    z = np.zeros_like(c)
    seg = hp.astype(int) % 6
    r1 = np.select(
        [seg == 0, seg == 1, seg == 2, seg == 3, seg == 4, seg == 5], [c, x, z, z, x, c]
    )
    g1 = np.select(
        [seg == 0, seg == 1, seg == 2, seg == 3, seg == 4, seg == 5], [x, c, c, x, z, z]
    )
    b1 = np.select(
        [seg == 0, seg == 1, seg == 2, seg == 3, seg == 4, seg == 5], [z, z, x, c, c, x]
    )
    m = lum - c * 0.5
    out = np.stack([r1 + m, g1 + m, b1 + m], axis=-1)
    # Where the pixel was grey (no hue), keep the original colour untouched.
    out = np.where(mask[..., None], out, rgb)
    return _to_img(out, img)


def _op_color_grade(img: Image.Image, op: Any) -> Image.Image:
    """Colour grade: tint shadows, midtones and highlights separately."""
    rgb = _rgb(img)
    lum = _luminance(rgb)
    out = rgb.copy()
    for zone, centre in (("shadows", 0.15), ("midtones", 0.5), ("highlights", 0.85)):
        h = _num(op, f"{zone}_hue", 0.0)
        s = _num(op, f"{zone}_sat", 0.0)
        if h == 0.0 and s == 0.0:
            continue
        weight = np.exp(-((lum - centre) ** 2) / (2.0 * 0.18**2))[..., None]
        tint_rgb = np.array(_hsv_to_rgb(h, s))[None, None, :]
        out = out + (tint_rgb - out) * weight * s * 0.5
    return _to_img(out, img)


def _hsv_to_rgb(hue: float, sat: float) -> tuple[float, float, float]:
    """Single HSV colour -> RGB tuple in [0,1]."""
    c = sat
    hp = (hue % 360.0) / 60.0
    x = c * (1.0 - abs(hp % 2.0 - 1.0))
    if hp < 1:
        r, g, b = c, x, 0.0
    elif hp < 2:
        r, g, b = x, c, 0.0
    elif hp < 3:
        r, g, b = 0.0, c, x
    elif hp < 4:
        r, g, b = 0.0, x, c
    elif hp < 5:
        r, g, b = x, 0.0, c
    else:
        r, g, b = c, 0.0, x
    return (r, g, b)


def _op_split_toning(img: Image.Image, op: Any) -> Image.Image:
    """Split toning: one colour for highlights, one for shadows."""
    rgb = _rgb(img)
    lum = _luminance(rgb)
    out = rgb.copy()
    for zone, _centre in (("shadows", 0.0), ("highlights", 1.0)):
        h = _num(op, f"{zone}_hue", 0.0)
        s = _num(op, f"{zone}_sat", 0.0)
        balance = _num(op, "balance", 0.0)
        if h == 0.0 and s == 0.0:
            continue
        if zone == "shadows":
            weight = np.clip(1.0 - lum / (0.5 + balance * 0.5), 0.0, 1.0)
        else:
            weight = np.clip((lum - (0.5 + balance * 0.5)) / 0.5, 0.0, 1.0)
        tint_rgb = _hsv_to_rgb(h, s)
        out = out + (np.array(tint_rgb)[None, None, :] - out) * weight[..., None] * s
    return _to_img(out, img)


# --- Detail ------------------------------------------------------------------


def _op_noise_reduce(img: Image.Image, op: Any) -> Image.Image:
    """Reduce sensor noise. Uses OpenCV fastNlMeans when available, else median."""
    strength = _clamp01(_num(op, "strength", 0.5))
    if strength <= 0.0:
        return img
    try:
        import cv2
    except ImportError:
        cv2 = None  # type: ignore[assignment]
    rgb_arr = np.asarray(img.convert("RGB"))
    if cv2 is not None:
        h = 3.0 + strength * 7.0
        cleaned = cv2.fastNlMeansDenoisingColored(rgb_arr, None, h, h, 7, 21)
        out = Image.fromarray(cleaned, mode="RGB").convert("RGBA")
    else:
        radius = max(1, int(strength * 3))
        out = img.filter(ImageFilter.MedianFilter(radius)).convert("RGBA")
    out.putalpha(img.getchannel("A"))
    return out


def _op_clarity(img: Image.Image, op: Any) -> Image.Image:
    """Local contrast (mid-frequency) — the Capture-One 'Clarity' slider."""
    amount = _num(op, "amount", 0.0)
    if amount == 0.0:
        return img
    rgb = img.convert("RGB")
    blurred = rgb.filter(ImageFilter.GaussianBlur(radius=12))
    # High-pass = original - blurred; add scaled back for local contrast.
    hp = ImageEnhance.Contrast(rgb).enhance(1.0 + amount * 0.8)
    return Image.blend(blurred, hp, 0.5).convert("RGBA")


def _op_texture(img: Image.Image, op: Any) -> Image.Image:
    """Enhance fine surface detail (high-frequency)."""
    amount = _num(op, "amount", 0.0)
    if amount == 0.0:
        return img
    rgb = img.convert("RGB")
    blurred = rgb.filter(ImageFilter.GaussianBlur(radius=2))
    hp = ImageChopsSubtract(rgb, blurred)
    enhanced = ImageChopsAdd(rgb, hp.point(lambda v: int(v * amount)))
    return enhanced.convert("RGBA")


def _op_dehaze(img: Image.Image, op: Any) -> Image.Image:
    """Remove atmospheric haze: boost low-frequency contrast and saturation."""
    amount = _clamp01(_num(op, "amount", 0.5))
    if amount <= 0.0:
        return img
    rgb = img.convert("RGB")
    blurred = rgb.filter(ImageFilter.GaussianBlur(radius=30))
    # Estimate haze as a bright, desaturated low-frequency layer and subtract.
    haze = ImageEnhance.Color(blurred).enhance(0.2)
    corrected = ImageChopsSubtract(rgb, haze.point(lambda v: int(v * amount * 0.5)))
    corrected = ImageEnhance.Contrast(corrected).enhance(1.0 + amount * 0.4)
    corrected = ImageEnhance.Color(corrected).enhance(1.0 + amount * 0.3)
    return corrected.convert("RGBA")


def ImageChopsSubtract(a: Image.Image, b: Image.Image) -> Image.Image:
    """Channel-wise subtraction with clipping (local helper)."""
    from PIL import ImageChops

    return ImageChops.subtract(a, b)


def ImageChopsAdd(a: Image.Image, b: Image.Image) -> Image.Image:
    """Channel-wise addition with clipping (local helper)."""
    from PIL import ImageChops

    return ImageChops.add(a, b)


# --- Local adjustments -------------------------------------------------------


def _feather_mask(img: Image.Image, op: Any) -> np.ndarray:
    """Build a soft 0..1 mask for the requested local-adjustment shape."""
    if np is None:
        _fail("NumPy is required for local adjustments.")
    w, h = img.size
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    shape = str(op.params.get("shape", "radial")).lower()
    feather = max(0.0, min(1.0, _num(op, "feather", 0.3)))
    if shape == "gradient":
        angle = math.radians(_num(op, "angle", 90.0))  # 90 = top->bottom
        dx = math.cos(angle)
        dy = math.sin(angle)
        cx = w * _clamp01(_num(op, "cx", 0.5))
        cy = h * _clamp01(_num(op, "cy", 0.5))
        proj = (xx - cx) * dx + (yy - cy) * dy
        length = math.hypot(w, h) * 0.5
        mask: np.ndarray = np.clip(0.5 + proj / length, 0.0, 1.0)
        return mask
    cx = w * _clamp01(_num(op, "cx", 0.5))
    cy = h * _clamp01(_num(op, "cy", 0.5))
    rx = max(1.0, w * _clamp01(_num(op, "rx", 0.4)))
    ry = max(1.0, h * _clamp01(_num(op, "ry", 0.4)))
    if shape == "rect":
        dist = np.maximum(np.abs(xx - cx) / rx, np.abs(yy - cy) / ry)
    else:  # radial / ellipse
        dist = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)
    edge = 1.0 + feather
    result: np.ndarray = np.clip(edge - dist, 0.0, 1.0)
    return result


def _op_local_adjust(img: Image.Image, op: Any) -> Image.Image:
    """Apply a tone/colour adjustment inside a soft-edged local mask."""
    mask = _feather_mask(img, op)
    if float(mask.max()) <= 0.0:
        return img
    rgb = _rgb(img)
    out = rgb.copy()
    brightness = _num(op, "brightness", 0.0)
    contrast = _num(op, "contrast", 0.0)
    saturation = _num(op, "saturation", 0.0)
    temperature = _num(op, "temperature", 0.0)
    if brightness:
        out = out + brightness * 0.2
    if contrast:
        gray = _luminance(out)[..., None]
        out = gray + (out - gray) * (1.0 + contrast)
    if saturation:
        gray = _luminance(out)[..., None]
        out = gray + (out - gray) * (1.0 + saturation)
    if temperature:
        out[..., 0] *= 1.0 + temperature * 0.15
        out[..., 2] *= 1.0 - temperature * 0.15
    blended = rgb * (1.0 - mask[..., None]) + out * mask[..., None]
    return _to_img(blended, img)


def _op_radial_filter(img: Image.Image, op: Any) -> Image.Image:
    """Radial filter: brighten/darken a feathered elliptical region."""
    return _op_local_adjust(img, op)


def _op_gradient_filter(img: Image.Image, op: Any) -> Image.Image:
    """Graduated filter: a feathered linear gradient adjustment."""
    return _op_local_adjust(img, op)


def _op_brush(img: Image.Image, op: Any) -> Image.Image:
    """Brush: apply an adjustment to a hand-drawn mask (polygon or ellipse)."""
    return _op_local_adjust(img, op)


# --- Retouch -----------------------------------------------------------------


def _op_spot_heal(img: Image.Image, op: Any) -> Image.Image:
    """Heal a small defect by blending in surrounding texture."""
    cx = _num(op, "cx", 0.5)
    cy = _num(op, "cy", 0.5)
    radius = max(1.0, _num(op, "radius", 0.03) * max(img.size))
    mask = Image.new("L", img.size, 0)
    draw = ImageDraw.Draw(mask)
    x, y = int(cx * img.width), int(cy * img.height)
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(radius * 0.5))
    smoothed = img.filter(ImageFilter.MedianFilter(size=max(3, int(radius))))
    return Image.composite(smoothed, img, mask)


def _op_clone_stamp(img: Image.Image, op: Any) -> Image.Image:
    """Copy a source rectangle onto a destination rectangle (clone stamp)."""
    sx = _num(op, "sx", 0.5)
    sy = _num(op, "sy", 0.5)
    dx = _num(op, "dx", 0.5)
    dy = _num(op, "dy", 0.5)
    width = max(1.0, _num(op, "width", 0.2) * img.width)
    height = max(1.0, _num(op, "height", 0.2) * img.height)
    src_box = (
        int(sx * img.width - width / 2),
        int(sy * img.height - height / 2),
        int(sx * img.width + width / 2),
        int(sy * img.height + height / 2),
    )
    dst_box = (
        int(dx * img.width - width / 2),
        int(dy * img.height - height / 2),
        int(dx * img.width + width / 2),
        int(dy * img.height + height / 2),
    )
    patch = img.crop(src_box).resize((dst_box[2] - dst_box[0], dst_box[3] - dst_box[1]))
    out = img.copy()
    out.paste(patch, (dst_box[0], dst_box[1]))
    return out


def _op_red_eye(img: Image.Image, op: Any) -> Image.Image:
    """Desaturate reddish pupils inside a mask region."""
    if np is None:
        _fail("NumPy is required for this operation.")
    cx = _num(op, "cx", 0.5)
    cy = _num(op, "cy", 0.5)
    radius = max(1.0, _num(op, "radius", 0.025) * max(img.size))
    rgb = _rgb(img)
    yy, xx = np.mgrid[0 : img.height, 0 : img.width].astype(np.float32)
    center = (cx * img.width, cy * img.height)
    dist = np.sqrt((xx - center[0]) ** 2 + (yy - center[1]) ** 2)
    region = dist <= radius
    red = rgb[..., 0]
    green = rgb[..., 1]
    blue = rgb[..., 2]
    reddish = (red > 0.5) & (red > green * 1.4) & (red > blue * 1.4) & region
    gray = _luminance(rgb)
    for c in range(3):
        rgb[..., c] = np.where(reddish, gray, rgb[..., c])
    return _to_img(rgb, img)


def _op_liquify(img: Image.Image, op: Any) -> Image.Image:
    """Mesh warp: bulge or pinch around a centre point."""
    if np is None:
        _fail("NumPy is required for this operation.")
    strength = _num(op, "strength", 0.0)  # +bulge, -pinch
    if strength == 0.0:
        return img
    cx = _num(op, "cx", 0.5) * img.width
    cy = _num(op, "cy", 0.5) * img.height
    radius = max(1.0, _num(op, "radius", 0.3) * max(img.size))
    yy, xx = np.mgrid[0 : img.height, 0 : img.width].astype(np.float32)
    dx = xx - cx
    dy = yy - cy
    dist = np.sqrt(dx**2 + dy**2)
    inside = dist < radius
    factor = np.where(inside, (dist / radius) ** 2, 1.0)
    displacement = 1.0 + strength * (1.0 - factor) * 0.5
    nx = np.where(inside, cx + dx * displacement, xx)
    ny = np.where(inside, cy + dy * displacement, yy)
    rgb_arr = np.asarray(img.convert("RGB"))
    warped = _remap(rgb_arr, nx, ny)
    out = Image.fromarray(warped, mode="RGB").convert("RGBA")
    out.putalpha(img.getchannel("A"))
    return out


def _remap(src: np.ndarray, map_x: np.ndarray, map_y: np.ndarray) -> np.ndarray:
    """Bilinear remap of a uint8 HxWxC array using OpenCV, else nearest-neighbour."""
    try:
        import cv2
    except ImportError:
        cv2 = None  # type: ignore[assignment]
    if cv2 is not None:
        return cv2.remap(
            src,
            map_x.astype(np.float32),
            map_y.astype(np.float32),
            cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REPLICATE,
        )
    # Nearest-neighbour fallback (no OpenCV).
    ix = np.clip(np.round(map_x).astype(int), 0, src.shape[1] - 1)
    iy = np.clip(np.round(map_y).astype(int), 0, src.shape[0] - 1)
    return src[iy, ix]


def _op_dodge_burn(img: Image.Image, op: Any) -> Image.Image:
    """Selectively brighten (dodge) or darken (burn) a masked region."""
    amount = _num(op, "amount", 0.0)  # +dodge, -burn
    if amount == 0.0:
        return img
    mask = _feather_mask(img, op)
    rgb = _rgb(img)
    if amount > 0:
        rgb = rgb + (1.0 - rgb) * amount * mask[..., None] * 0.6
    else:
        rgb = rgb * (1.0 + amount * mask[..., None] * 0.6)
    return _to_img(rgb, img)


def _op_frequency_separation(img: Image.Image, op: Any) -> Image.Image:
    """Skin-smooth by softening the low-frequency layer, keeping texture."""
    amount = _clamp01(_num(op, "amount", 0.5))
    if amount <= 0.0:
        return img
    rgb = img.convert("RGB")
    low = rgb.filter(ImageFilter.GaussianBlur(radius=6))
    high = ImageChopsSubtract(rgb, low)
    softened_low = low.filter(ImageFilter.GaussianBlur(radius=int(1 + amount * 3)))
    out = ImageChopsAdd(softened_low, high)
    return out.convert("RGBA")


# --- Transform ---------------------------------------------------------------


def _op_straighten(img: Image.Image, op: Any) -> Image.Image:
    """Straighten a tilted horizon. Uses a given angle, or detects edges."""
    angle = _num(op, "angle", 0.0)
    if angle == 0.0:
        try:
            angle = _detect_tilt(img)
        except Exception:  # noqa: BLE001 - detection is best-effort
            angle = 0.0
    if angle == 0.0:
        return img
    return img.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)


def _detect_tilt(img: Image.Image) -> float:
    """Estimate rotation from dominant edge orientation (best-effort)."""
    try:
        import cv2
    except ImportError:
        return 0.0
    gray = np.asarray(img.convert("L"))
    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, math.pi / 180, threshold=80, minLineLength=60)
    if lines is None:
        return 0.0
    angles = []
    for line in lines[:, 0]:
        x1, y1, x2, y2 = line
        if abs(x2 - x1) < 1e-6:
            continue
        ang = math.degrees(math.atan2(y2 - y1, x2 - x1))
        # Prefer near-horizontal lines.
        if abs(ang) < 45.0:
            angles.append(ang)
    if not angles:
        return 0.0
    return -sum(angles) / len(angles)


def _op_perspective(img: Image.Image, op: Any) -> Image.Image:
    """Four-corner perspective warp (keystone correction)."""
    if np is None:
        _fail("NumPy is required for this operation.")
    try:
        import cv2
    except ImportError:
        _fail("perspective requires OpenCV.")
    w, h = img.size
    src = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], dtype=np.float32)
    tl = (_num(op, "tl_x", 0.0), _num(op, "tl_y", 0.0))
    tr = (_num(op, "tr_x", 1.0), _num(op, "tr_y", 0.0))
    br = (_num(op, "br_x", 1.0), _num(op, "br_y", 1.0))
    bl = (_num(op, "bl_x", 0.0), _num(op, "bl_y", 1.0))
    dst = np.array(
        [
            [tl[0] * w, tl[1] * h],
            [tr[0] * w, tr[1] * h],
            [br[0] * w, br[1] * h],
            [bl[0] * w, bl[1] * h],
        ],
        dtype=np.float32,
    )
    matrix = cv2.getPerspectiveTransform(src, dst)
    rgb_arr = np.asarray(img.convert("RGB"))
    warped = cv2.warpPerspective(
        rgb_arr, matrix, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE
    )
    out = Image.fromarray(warped, mode="RGB").convert("RGBA")
    out.putalpha(img.getchannel("A"))
    return out


def _op_lens_correction(img: Image.Image, op: Any) -> Image.Image:
    """Barrel/pincushion radial distortion correction."""
    if np is None:
        _fail("NumPy is required for this operation.")
    k1 = _num(op, "k1", 0.0)
    if k1 == 0.0:
        return img
    w, h = img.size
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = w / 2.0, h / 2.0
    nx = (xx - cx) / cx
    ny = (yy - cy) / cy
    r2 = nx**2 + ny**2
    scale = 1.0 + k1 * r2
    map_x = cx + (xx - cx) / scale
    map_y = cy + (yy - cy) / scale
    rgb_arr = np.asarray(img.convert("RGB"))
    warped = _remap(rgb_arr, map_x, map_y)
    out = Image.fromarray(warped, mode="RGB").convert("RGBA")
    out.putalpha(img.getchannel("A"))
    return out


# --- Effects -----------------------------------------------------------------


def _op_grain(img: Image.Image, op: Any) -> Image.Image:
    """Add film grain (monochrome noise)."""
    if np is None:
        _fail("NumPy is required for this operation.")
    amount = _clamp01(_num(op, "amount", 0.2))
    if amount <= 0.0:
        return img
    rng = np.random.default_rng(_int_seed(op))
    noise = rng.normal(0.0, amount * 0.15, (img.height, img.width, 1)).astype(
        np.float32
    )
    rgb = _rgb(img)
    rgb = rgb + noise
    return _to_img(rgb, img)


def _int_seed(op: Any) -> int:
    try:
        return int(op.params.get("seed", 0))
    except (TypeError, ValueError):
        return 0


def _op_watermark(img: Image.Image, op: Any) -> Image.Image:
    """Stamp a semi-transparent text watermark."""
    text = str(op.params.get("text", ""))
    if not text:
        return img
    size = int(max(8, min(400, _num(op, "size", 32))))
    opacity = _clamp01(_num(op, "opacity", 0.5))
    position = str(op.params.get("position", "bottom-right"))
    color = str(op.params.get("color", "#ffffff"))
    overlay = img.copy()
    draw = ImageDraw.Draw(overlay)
    font: Any
    try:
        font = ImageFont.truetype("arial.ttf", size)
    except Exception:  # noqa: BLE001 - font availability varies by OS
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    margin = int(size * 0.5)
    anchors = {
        "top-left": (margin, margin),
        "top-right": (img.width - tw - margin, margin),
        "bottom-left": (margin, img.height - th - margin),
        "bottom-right": (img.width - tw - margin, img.height - th - margin),
        "center": ((img.width - tw) // 2, (img.height - th) // 2),
    }
    xy = anchors.get(position, anchors["bottom-right"])
    draw.text(xy, text, font=font, fill=color)
    return Image.blend(img, overlay, opacity)


def _op_motion_blur(img: Image.Image, op: Any) -> Image.Image:
    """Directional motion blur (rolling-average along the direction)."""
    if np is None:
        _fail("NumPy is required for this operation.")
    angle = _num(op, "angle", 0.0)
    distance = max(0.0, _num(op, "distance", 10.0))
    if distance <= 0.0:
        return img
    rad = math.radians(angle)
    dx = math.cos(rad)
    dy = math.sin(rad)
    steps = max(2, int(distance))
    base = np.asarray(img.convert("RGB"), dtype=np.float32)
    acc = np.zeros_like(base)
    for i in range(steps + 1):
        t = i / steps
        ox = round(dx * distance * (t - 0.5))
        oy = round(dy * distance * (t - 0.5))
        acc += np.roll(base, (oy, ox), axis=(0, 1))
    result = acc / (steps + 1)
    out = Image.fromarray(result.astype(np.uint8), mode="RGB").convert("RGBA")
    out.putalpha(img.getchannel("A"))
    return out


def _op_lens_blur(img: Image.Image, op: Any) -> Image.Image:
    """Zoom/radial blur toward the centre."""
    if np is None:
        _fail("NumPy is required for this operation.")
    amount = _clamp01(_num(op, "amount", 0.5))
    if amount <= 0.0:
        return img
    w, h = img.size
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = w / 2.0, h / 2.0
    scale = 1.0 + amount * 0.6
    map_x = cx + (xx - cx) / scale
    map_y = cy + (yy - cy) / scale
    rgb_arr = np.asarray(img.convert("RGB"))
    warped = _remap(rgb_arr, map_x, map_y)
    out = Image.fromarray(warped, mode="RGB").convert("RGBA")
    out.putalpha(img.getchannel("A"))
    return out


# --- Registry ----------------------------------------------------------------

#: Extended ops keyed by name. Registered into ``image_engine._OPS``.
PHOTO_OPS: dict[str, Any] = {
    # light
    "exposure": _op_exposure,
    "highlights": _op_highlights,
    "shadows": _op_shadows,
    "whites": _op_whites,
    "blacks": _op_blacks,
    "levels": _op_levels,
    # colour
    "white_balance": _op_white_balance,
    "temperature": _op_temperature,
    "tint": _op_tint,
    "vibrance": _op_vibrance,
    "hsl": _op_hsl,
    "color_grade": _op_color_grade,
    "split_toning": _op_split_toning,
    # detail
    "noise_reduce": _op_noise_reduce,
    "clarity": _op_clarity,
    "texture": _op_texture,
    "dehaze": _op_dehaze,
    # local
    "local_adjust": _op_local_adjust,
    "radial_filter": _op_radial_filter,
    "gradient_filter": _op_gradient_filter,
    "brush": _op_brush,
    # retouch
    "spot_heal": _op_spot_heal,
    "clone_stamp": _op_clone_stamp,
    "red_eye": _op_red_eye,
    "liquify": _op_liquify,
    "dodge_burn": _op_dodge_burn,
    "frequency_separation": _op_frequency_separation,
    # transform
    "straighten": _op_straighten,
    "perspective": _op_perspective,
    "lens_correction": _op_lens_correction,
    # effects
    "grain": _op_grain,
    "watermark": _op_watermark,
    "motion_blur": _op_motion_blur,
    "lens_blur": _op_lens_blur,
}
