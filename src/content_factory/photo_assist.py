"""Accessibility layer for the photo engine.

Two audiences must be able to use every photo function:

* **Vision users** get a live histogram and plain-language descriptions of what
  each slider does.
* **Non-vision users and AI agents** get a natural-language description of the
  image itself, a per-operation plain-language explanation, and histogram-based
  auto-suggestions — so a task can be driven entirely by text with no pixels
  ever seen.

Everything here is deterministic and offline: it reads real pixel statistics
(histogram, luminance, channel casts, saturation, sharpness) and turns them
into words. A pluggable vision model can be swapped in later without changing
the call sites.
"""

from __future__ import annotations

from typing import Any

from PIL import Image, ImageFilter, ImageStat

from . import image_engine
from .catalog import detail, grouped_catalog

__all__ = [
    "OP_DOCS",
    "catalog",
    "describe_image",
    "describe_op",
    "histogram",
    "suggest_edits",
]


#: Plain-language documentation for every op, grouped by category. Keys match
#: the op names in the engine so a description always exists for a known op.
OP_DOCS: dict[str, dict[str, Any]] = {
    # --- basic ---------------------------------------------------------------
    "crop": {
        "category": "basic",
        "description": "Cut away unwanted edges and change the frame to a new "
        "rectangle. Give left/top/width/height (in pixels) of the region to keep.",
        "params": {
            "left": "Distance from the left edge (pixels).",
            "top": "Distance from the top edge (pixels).",
            "width": "How wide the kept region is (pixels).",
            "height": "How tall the kept region is (pixels).",
        },
    },
    "resize": {
        "category": "basic",
        "description": "Change the image resolution. With fit on, it scales to "
        "fit inside width x height without distorting.",
        "params": {
            "width": "Target width (pixels).",
            "height": "Target height (pixels).",
        },
    },
    "rotate": {
        "category": "basic",
        "description": "Spin the image by a number of degrees. Positive rotates "
        "counter-clockwise; the canvas grows to fit unless expand is off.",
        "params": {
            "degrees": "Angle to rotate by.",
            "expand": "Grow the canvas to fit.",
        },
    },
    "flip": {
        "category": "basic",
        "description": "Mirror the image horizontally or vertically.",
        "params": {"horizontal": "Mirror left-right (true) or top-bottom (false)."},
    },
    "padding": {
        "category": "basic",
        "description": "Place the image centered on an exact canvas, filling the "
        "rest with a colour. Use to letterbox to a platform size.",
        "params": {
            "width": "Canvas width.",
            "height": "Canvas height.",
            "color": "Fill colour.",
        },
    },
    # --- light ---------------------------------------------------------------
    "tone": {
        "category": "light",
        "description": "Simple brightness, contrast and saturation in one step. "
        "1.0 means unchanged; above brightens / strengthens, below darkens.",
        "params": {
            "brightness": "Overall brightness (1.0 = unchanged).",
            "contrast": "Difference between light and dark areas.",
            "saturation": "Strength of all colours.",
        },
    },
    "exposure": {
        "category": "light",
        "description": "Brighten or darken the whole image in photographic "
        "stops, like turning the exposure dial. +1 doubles the light, -1 halves it.",
        "params": {"ev": "Exposure in stops (e.g. 0.5, -1.0)."},
    },
    "highlights": {
        "category": "light",
        "description": "Recover detail in blown-out bright areas by pulling them "
        "back toward mid-tones. Use when the sky or a lamp is pure white.",
        "params": {"amount": "How strongly to recover bright detail (0..1)."},
    },
    "shadows": {
        "category": "light",
        "description": "Reveal detail hiding in dark areas by lifting them. Use "
        "when faces or subjects are lost in shadow.",
        "params": {"amount": "How strongly to lift shadows (0..1)."},
    },
    "whites": {
        "category": "light",
        "description": "Move the absolute white point: clip the brightest pixels "
        "or lift the top of the range.",
        "params": {"amount": "-1..1; negative clips whites, positive lifts them."},
    },
    "blacks": {
        "category": "light",
        "description": "Move the absolute black point: crush the darkest pixels "
        "or lift the bottom of the range.",
        "params": {"amount": "-1..1; negative crushes blacks, positive lifts them."},
    },
    "levels": {
        "category": "light",
        "description": "Remap the tonal range with a black point, a white point "
        "and a gamma curve. The most precise way to set contrast.",
        "params": {
            "black": "Black point (0..1).",
            "white": "White point (0..1).",
            "gamma": "Mid-tone curve (>1 darkens mids, <1 brightens).",
        },
    },
    "curves": {
        "category": "light",
        "description": "Fine tonal control over shadows, mid-tones and highlights "
        "together, like dragging points on a curve.",
        "params": {
            "shadows": "Lift or lower shadows.",
            "mids": "Adjust mid-tones.",
            "highlights": "Lift or lower highlights.",
        },
    },
    # --- colour --------------------------------------------------------------
    "color_balance": {
        "category": "colour",
        "description": "Shift the red, green and blue channels independently to "
        "correct or stylise colour.",
        "params": {
            "red": "Red shift (-1..1).",
            "green": "Green shift.",
            "blue": "Blue shift.",
        },
    },
    "white_balance": {
        "category": "colour",
        "description": "Fix a colour cast so whites look neutral. Temperature "
        "makes the photo warmer (amber) or cooler (blue); tint shifts green "
        "vs magenta.",
        "params": {
            "temperature": "-1..1; positive warmer, negative cooler.",
            "tint": "-1..1; positive more magenta, negative more green.",
        },
    },
    "temperature": {
        "category": "colour",
        "description": "Warmth axis of white balance: amber vs blue.",
        "params": {"temperature": "-1..1; positive warmer, negative cooler."},
    },
    "tint": {
        "category": "colour",
        "description": "Tint axis of white balance: green vs magenta.",
        "params": {"tint": "-1..1; positive more magenta, negative more green."},
    },
    "vibrance": {
        "category": "colour",
        "description": "Boost muted colours while leaving already-vivid colours "
        "(and skin tones) mostly alone. Safer than saturation for portraits.",
        "params": {"amount": "-1..1; positive boosts muted colours."},
    },
    "hsl": {
        "category": "colour",
        "description": "Colour mixer: change the hue, saturation or lightness of "
        "a single colour range (red, orange, yellow, green, cyan, blue, purple, "
        "magenta) without touching the others.",
        "params": {
            "red_hue": "Shift the red hue (degrees).",
            "red_sat": "Change red saturation.",
            "red_lum": "Change red lightness.",
            "green_hue": "Shift the green hue.",
            "green_sat": "Change green saturation.",
            "green_lum": "Change green lightness.",
            "blue_hue": "Shift the blue hue.",
            "blue_sat": "Change blue saturation.",
            "blue_lum": "Change blue lightness.",
        },
    },
    "color_grade": {
        "category": "colour",
        "description": "Add a colour wash to shadows, mid-tones and highlights "
        "separately, for a cinematic look.",
        "params": {
            "shadows_hue": "Hue for the shadows.",
            "shadows_sat": "Strength of the shadow tint.",
            "midtones_hue": "Hue for the mid-tones.",
            "midtones_sat": "Strength of the mid-tone tint.",
            "highlights_hue": "Hue for the highlights.",
            "highlights_sat": "Strength of the highlight tint.",
        },
    },
    "split_toning": {
        "category": "colour",
        "description": "Tint the highlights one colour and the shadows another — "
        "the classic film look.",
        "params": {
            "shadows_hue": "Colour for the shadows.",
            "shadows_sat": "Strength of the shadow colour.",
            "highlights_hue": "Colour for the highlights.",
            "highlights_sat": "Strength of the highlight colour.",
            "balance": "Where the split sits (-1..1).",
        },
    },
    "filter": {
        "category": "colour",
        "description": "Apply a ready-made look (LUT-style preset): grayscale, "
        "sepia, noir, vintage, cool, warm, vivid, fade.",
        "params": {"preset": "The named look to apply."},
    },
    # --- detail --------------------------------------------------------------
    "sharpen": {
        "category": "detail",
        "description": "Increase perceived sharpness by boosting edge contrast.",
        "params": {"percent": "0..500; how much to sharpen."},
    },
    "noise_reduce": {
        "category": "detail",
        "description": "Remove sensor noise / grain from low-light shots while "
        "keeping edges. Stronger values soften detail more.",
        "params": {"strength": "0..1; how aggressively to denoise."},
    },
    "clarity": {
        "category": "detail",
        "description": "Increase mid-frequency local contrast so textures and "
        "surfaces pop without a harsh edge.",
        "params": {"amount": "-1..1; positive increases local contrast."},
    },
    "texture": {
        "category": "detail",
        "description": "Emphasise fine surface detail (skin pores, fabric, rock).",
        "params": {"amount": "-1..1; positive emphasises fine detail."},
    },
    "dehaze": {
        "category": "detail",
        "description": "Remove atmospheric haze or fog and restore contrast and "
        "colour depth.",
        "params": {"amount": "0..1; how much haze to remove."},
    },
    # --- local ---------------------------------------------------------------
    "local_adjust": {
        "category": "local",
        "description": "Apply a brightness / contrast / saturation / warmth "
        "adjustment only inside a soft-edged region.",
        "params": {
            "shape": "radial, gradient or rect.",
            "cx": "Centre x (0..1).",
            "cy": "Centre y (0..1).",
            "rx": "Horizontal radius (0..1).",
            "ry": "Vertical radius (0..1).",
            "feather": "Softness of the mask edge (0..1).",
            "brightness": "Local brightness change.",
            "contrast": "Local contrast change.",
            "saturation": "Local saturation change.",
        },
    },
    "radial_filter": {
        "category": "local",
        "description": "Adjust a feathered oval region — commonly used to "
        "brighten the subject and draw the eye inward.",
        "params": {
            "cx": "Centre x.",
            "cy": "Centre y.",
            "rx": "Radius x.",
            "ry": "Radius y.",
        },
    },
    "gradient_filter": {
        "category": "local",
        "description": "Adjust a gradual band across the image — commonly used "
        "to darken or enrich a sky.",
        "params": {
            "angle": "Direction of the gradient (degrees).",
            "feather": "Edge softness.",
        },
    },
    "brush": {
        "category": "local",
        "description": "Paint an adjustment onto a hand-drawn region.",
        "params": {"shape": "radial or rect.", "cx": "Centre x.", "cy": "Centre y."},
    },
    "vignette": {
        "category": "local",
        "description": "Darken or lighten the corners to focus attention on the "
        "centre.",
        "params": {"strength": "0..1; how strong the corner shading is."},
    },
    # --- retouch -------------------------------------------------------------
    "spot_heal": {
        "category": "retouch",
        "description": "Remove a small blemish or dust speck by blending in the "
        "surrounding texture.",
        "params": {
            "cx": "Centre x.",
            "cy": "Centre y.",
            "radius": "Patch size (fraction of the image).",
        },
    },
    "clone_stamp": {
        "category": "retouch",
        "description": "Copy one rectangular region onto another to hide an "
        "object or repair an area.",
        "params": {
            "sx": "Source centre x.",
            "sy": "Source centre y.",
            "dx": "Destination centre x.",
            "dy": "Destination centre y.",
            "width": "Region width (fraction).",
            "height": "Region height (fraction).",
        },
    },
    "inpaint": {
        "category": "retouch",
        "description": "Fill a masked region by reconstructing plausible pixels "
        "from the surroundings — content-aware fill.",
        "params": {
            "mask_b64": "Base64 mask image.",
            "method": "telea or navier-stokes.",
            "radius": "Fill radius.",
        },
    },
    "red_eye": {
        "category": "retouch",
        "description": "Desaturate reddish pupils caused by flash.",
        "params": {
            "cx": "Eye centre x.",
            "cy": "Eye centre y.",
            "radius": "Affected radius.",
        },
    },
    "liquify": {
        "category": "retouch",
        "description": "Warp the image by bulging or pinching around a point. "
        "Use sparingly on portraits.",
        "params": {
            "strength": "+bulge, -pinch.",
            "cx": "Centre x.",
            "cy": "Centre y.",
            "radius": "Affected radius.",
        },
    },
    "dodge_burn": {
        "category": "retouch",
        "description": "Selectively brighten (dodge) or darken (burn) a region "
        "to sculpt light and shape.",
        "params": {
            "amount": "+dodge, -burn.",
            "shape": "Mask shape.",
            "cx": "Centre x.",
            "cy": "Centre y.",
        },
    },
    "frequency_separation": {
        "category": "retouch",
        "description": "Smoothen skin by softening the low-frequency colour "
        "layer while keeping the high-frequency texture intact.",
        "params": {"amount": "0..1; how much to soften."},
    },
    # --- transform -----------------------------------------------------------
    "straighten": {
        "category": "transform",
        "description": "Correct a tilted horizon. Detects the tilt automatically "
        "or uses the angle you give.",
        "params": {"angle": "Manual angle (degrees); 0 = auto-detect."},
    },
    "perspective": {
        "category": "transform",
        "description": "Fix converging verticals (keystone) by moving the four "
        "corners of the frame.",
        "params": {
            "tl_x": "Top-left x (0..1).",
            "tl_y": "Top-left y.",
            "tr_x": "Top-right x.",
            "tr_y": "Top-right y.",
            "br_x": "Bottom-right x.",
            "br_y": "Bottom-right y.",
            "bl_x": "Bottom-left x.",
            "bl_y": "Bottom-left y.",
        },
    },
    "lens_correction": {
        "category": "transform",
        "description": "Correct barrel or pincushion distortion from the lens.",
        "params": {"k1": "Radial distortion coefficient (positive = barrel)."},
    },
    # --- effects -------------------------------------------------------------
    "blur": {
        "category": "effects",
        "description": "Soft Gaussian blur — great for backgrounds.",
        "params": {"radius": "Blur radius in pixels."},
    },
    "motion_blur": {
        "category": "effects",
        "description": "Blur along a direction to suggest movement.",
        "params": {
            "angle": "Direction (degrees).",
            "distance": "How far the blur travels.",
        },
    },
    "lens_blur": {
        "category": "effects",
        "description": "Radial zoom blur toward the centre.",
        "params": {"amount": "0..1; how strong the zoom blur is."},
    },
    "grain": {
        "category": "effects",
        "description": "Add film grain for an analog look.",
        "params": {
            "amount": "0..1; how much grain.",
            "seed": "Random seed for reproducibility.",
        },
    },
    "text": {
        "category": "effects",
        "description": "Draw text on the image.",
        "params": {
            "text": "The text.",
            "size": "Font size.",
            "color": "Text colour.",
            "position": "Anchor position.",
        },
    },
    "watermark": {
        "category": "effects",
        "description": "Stamp a semi-transparent copyright or logo text.",
        "params": {
            "text": "The watermark text.",
            "opacity": "0..1 transparency.",
            "position": "Anchor position.",
        },
    },
    # --- compound ------------------------------------------------------------
    "auto_enhance": {
        "category": "compound",
        "description": "One-click improvement: auto contrast, gentle colour "
        "boost and mild sharpening.",
        "params": {},
    },
    "remove_background": {
        "category": "compound",
        "description": "Remove a solid-colour background (chroma-key) or the "
        "border-average colour automatically.",
        "params": {
            "color": "Hex colour or 'auto'.",
            "tolerance": "0..1 how close to the key colour.",
        },
    },
}

#: Category ordering for the catalogue.
CATEGORY_ORDER = [
    "basic",
    "light",
    "colour",
    "detail",
    "local",
    "retouch",
    "transform",
    "effects",
    "compound",
]


def catalog() -> dict[str, Any]:
    """Return the full op catalogue grouped by category, with descriptions.

    Driven by the engine's registered ops rather than by ``OP_DOCS``: an op that
    exists but is not documented yet still appears, under ``other``, instead of
    silently vanishing from the catalogue an agent plans against.
    """
    docs = {
        name: OP_DOCS.get(
            name, {"category": "other", "description": name, "params": {}}
        )
        for name in image_engine.KNOWN_OPS
    }
    return grouped_catalog(docs, CATEGORY_ORDER, presets=image_voice_presets())


def image_voice_presets() -> list[str]:
    """Named one-click looks (imported lazily to avoid a service import)."""
    from .image_voice_service import IMAGE_PRESETS

    return sorted(IMAGE_PRESETS)


def histogram(img: Image.Image) -> dict[str, Any]:
    """Compute per-channel and luminance histograms plus tonal statistics."""
    rgb = img.convert("RGB")
    stat = ImageStat.Stat(rgb)
    lum = ImageStat.Stat(ImageOps_grayscale(rgb))
    channels = {}
    for name, idx in (("red", 0), ("green", 1), ("blue", 2)):
        hist = rgb.histogram()[idx * 256 : (idx + 1) * 256]
        channels[name] = {
            "mean": round(stat.mean[idx], 1),
            "stddev": round(stat.stddev[idx], 1),
            "min": round(stat.extrema[idx][0], 1),
            "max": round(stat.extrema[idx][1], 1),
            "histogram": hist,
        }
    lum_hist = rgb.convert("L").histogram()
    return {
        "width": img.width,
        "height": img.height,
        "luminance": {
            "mean": round(lum.mean[0], 1),
            "stddev": round(lum.stddev[0], 1),
            "histogram": lum_hist,
        },
        "channels": channels,
    }


def ImageOps_grayscale(img: Image.Image) -> Image.Image:
    """Grayscale conversion helper."""
    from PIL import ImageOps

    return ImageOps.grayscale(img)


def describe_image(img: Image.Image) -> dict[str, Any]:
    """Turn pixel statistics into a plain-language description of the image.

    Deterministic and offline, so a non-vision user or an AI agent can know
    roughly what a photo looks like without ever seeing it.
    """
    h = histogram(img)
    lum_mean = h["luminance"]["mean"]
    lum_std = h["luminance"]["stddev"]
    r = h["channels"]["red"]["mean"]
    g = h["channels"]["green"]["mean"]
    b = h["channels"]["blue"]["mean"]

    # Brightness.
    if lum_mean < 60:
        brightness = "very dark / underexposed"
    elif lum_mean < 110:
        brightness = "dark / moody"
    elif lum_mean < 150:
        brightness = "balanced"
    elif lum_mean < 200:
        brightness = "bright"
    else:
        brightness = "very bright / possibly overexposed"

    # Contrast from luminance spread.
    if lum_std < 30:
        contrast = "flat / low contrast"
    elif lum_std < 60:
        contrast = "moderate contrast"
    else:
        contrast = "high contrast"

    # Dominant colour cast.
    mx = max(r, g, b)
    mn = min(r, g, b)
    if mx - mn < 8:
        cast = "neutral / no strong colour cast"
    elif r >= g and r >= b:
        cast = "warm / reddish cast"
    elif g >= r and g >= b:
        cast = "greenish cast"
    elif b >= r and b >= g:
        cast = "cool / bluish cast"
    else:
        cast = "mixed colour cast"

    # Saturation from channel spread averaged.
    avg_spread = (abs(r - g) + abs(g - b) + abs(r - b)) / 3.0
    if avg_spread < 12:
        saturation = "muted / low saturation"
    elif avg_spread < 40:
        saturation = "moderate saturation"
    else:
        saturation = "vivid / high saturation"

    # Sharpness via Laplacian variance (fallback: edge-energy of a downscale).
    sharpness = _sharpness_label(img)

    summary = (
        f"This image is {brightness} with {contrast}. Colours are {saturation} "
        f"with a {cast}. Overall it reads as {sharpness}."
    )
    return {
        "summary": summary,
        "details": {
            "brightness": brightness,
            "contrast": contrast,
            "colour_cast": cast,
            "saturation": saturation,
            "sharpness": sharpness,
        },
        "histogram": h,
    }


def _sharpness_label(img: Image.Image) -> str:
    try:
        import cv2
        import numpy as np
    except ImportError:
        # Fallback: edge-energy via PIL Sobel-ish (high-pass) on a downscale.
        small = img.convert("L").resize((64, 64))
        hp = small.filter(ImageFilter.FIND_EDGES)
        energy = sum(hp.getdata()) / (64 * 64)
        if energy < 6:
            return "soft / blurry"
        if energy < 20:
            return "moderately sharp"
        return "sharp"
    gray = np.asarray(img.convert("L"))
    lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    if lap_var < 40:
        return "soft / blurry"
    if lap_var < 200:
        return "moderately sharp"
    return "sharp"


def describe_op(name: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Explain one operation in plain language, with its current values."""
    name = name.lower()
    doc = OP_DOCS.get(name)
    if doc is None:
        if name in image_engine.KNOWN_OPS:
            doc = {"category": "other", "description": name, "params": {}}
        else:
            raise image_engine.ImageError(
                f"Unknown op '{name}'. Known: {sorted(image_engine.KNOWN_OPS)}"
            )
    values = {}
    for key in doc.get("params", {}):
        if params and key in params:
            values[key] = params[key]
    return {**detail(name, doc), "current_values": values}


def suggest_edits(img: Image.Image) -> dict[str, Any]:
    """Histogram-based auto-suggestions: a list of ops with reasons.

    Lets a non-vision user or agent get a sensible starting recipe from the
    pixel statistics alone.
    """
    h = histogram(img)
    lum_mean = h["luminance"]["mean"]
    lum_std = h["luminance"]["stddev"]
    r = h["channels"]["red"]["mean"]
    g = h["channels"]["green"]["mean"]
    b = h["channels"]["blue"]["mean"]

    suggestions: list[dict[str, Any]] = []

    if lum_mean < 80:
        suggestions.append(
            {
                "op": "exposure",
                "params": {"ev": 0.7},
                "reason": "The image is underexposed (mean luminance "
                f"{lum_mean:.0f}); brighten it by about two-thirds of a stop.",
            }
        )
    elif lum_mean > 200:
        suggestions.append(
            {
                "op": "exposure",
                "params": {"ev": -0.7},
                "reason": "The image is overexposed (mean luminance "
                f"{lum_mean:.0f}); darken it by about two-thirds of a stop.",
            }
        )

    if lum_std < 35:
        suggestions.append(
            {
                "op": "levels",
                "params": {"black": 0.02, "white": 0.98},
                "reason": f"Contrast is low (luminance spread {lum_std:.0f}); "
                "stretch the tonal range to add punch.",
            }
        )

    # Colour cast: warm/cool/green.
    if r - b > 18:
        suggestions.append(
            {
                "op": "white_balance",
                "params": {"temperature": -0.4},
                "reason": f"The image has a warm cast (red {r:.0f} vs blue "
                f"{b:.0f}); cool it down to neutralise.",
            }
        )
    elif b - r > 18:
        suggestions.append(
            {
                "op": "white_balance",
                "params": {"temperature": 0.4},
                "reason": f"The image has a cool cast (blue {b:.0f} vs red "
                f"{r:.0f}); warm it up to neutralise.",
            }
        )
    elif g - max(r, b) > 18:
        suggestions.append(
            {
                "op": "white_balance",
                "params": {"tint": 0.4},
                "reason": "The image has a green cast; shift the tint toward "
                "magenta to neutralise.",
            }
        )

    # Saturation.
    avg_spread = (abs(r - g) + abs(g - b) + abs(r - b)) / 3.0
    if avg_spread < 12:
        suggestions.append(
            {
                "op": "vibrance",
                "params": {"amount": 0.5},
                "reason": f"Colours are muted (average channel spread "
                f"{avg_spread:.0f}); boost vibrance to add life.",
            }
        )

    # Sharpness.
    try:
        import cv2
        import numpy as np
    except ImportError:
        cv2 = None  # type: ignore[assignment]
        np = None  # type: ignore[assignment]
    if cv2 is not None:
        gray = np.asarray(img.convert("L"))
        lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        if lap_var < 40:
            suggestions.append(
                {
                    "op": "sharpen",
                    "params": {"percent": 60},
                    "reason": f"The image looks soft (sharpness variance "
                    f"{lap_var:.0f}); sharpen it.",
                }
            )

    return {
        "suggestions": suggestions,
        "count": len(suggestions),
        "summary": (
            "No changes suggested — the image looks well-balanced."
            if not suggestions
            else "Suggested starting recipe based on the histogram."
        ),
    }
