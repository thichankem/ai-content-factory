"""Photo Lab models: blending, tone, layers and adjustments.

Mirrors the contract the studio's Photo Lab screen edits, and matches the
specification in ``docs/SPEC-IMAGE-EDITING.md``. Two rules drive every choice:

* a layer is **non-destructive**: it stores parameters, never pixels, so the
  same document renders identically on the backend and in the browser;
* the blending vocabulary is the 27-mode industry set, because a preset named
  ``multiply`` that silently becomes something else is the kind of contract
  drift that breaks a pipeline.
"""

from __future__ import annotations

import enum
from typing import Literal

from pydantic import BaseModel, Field


class BlendMode(enum.StrEnum):
    """The 27 industry-standard blending modes (Photoshop-compatible set)."""

    NORMAL = "normal"
    DISSOLVE = "dissolve"
    DARKEN = "darken"
    MULTIPLY = "multiply"
    COLOR_BURN = "color-burn"
    LINEAR_BURN = "linear-burn"
    DARKER_COLOR = "darker-color"
    LIGHTEN = "lighten"
    SCREEN = "screen"
    COLOR_DODGE = "color-dodge"
    LINEAR_DODGE = "linear-dodge"
    LIGHTER_COLOR = "lighter-color"
    OVERLAY = "overlay"
    SOFT_LIGHT = "soft-light"
    HARD_LIGHT = "hard-light"
    VIVID_LIGHT = "vivid-light"
    LINEAR_LIGHT = "linear-light"
    PIN_LIGHT = "pin-light"
    HARD_MIX = "hard-mix"
    DIFFERENCE = "difference"
    EXCLUSION = "exclusion"
    SUBTRACT = "subtract"
    DIVIDE = "divide"
    HUE = "hue"
    SATURATION = "saturation"
    COLOR = "color"
    LUMINOSITY = "luminosity"


class MaskShape(enum.StrEnum):
    """The shape an alpha mask is drawn as."""

    NONE = "none"
    RECTANGLE = "rectangle"
    CIRCLE = "circle"
    HEART = "heart"
    STAR = "star"


class ToneCurvePoint(BaseModel):
    """One control point of a tone curve (16-bit precision, clamped)."""


class HSLBand(BaseModel):
    """One colour band of an HSL balance adjustment."""

    hue_shift: float = Field(default=0.0, ge=-180.0, le=180.0)
    saturation: float = Field(default=0.0, ge=-100.0, le=100.0)
    luminance: float = Field(default=0.0, ge=-100.0, le=100.0)


class HSLBalance(BaseModel):
    """HSL adjustment across six named colour ranges."""

    reds: HSLBand = Field(default_factory=HSLBand)
    yellows: HSLBand = Field(default_factory=HSLBand)
    greens: HSLBand = Field(default_factory=HSLBand)
    cyans: HSLBand = Field(default_factory=HSLBand)
    blues: HSLBand = Field(default_factory=HSLBand)
    magentas: HSLBand = Field(default_factory=HSLBand)


class TextProperties(BaseModel):
    """Typography for a text layer (Premiere-style contextual properties)."""

    font_family: str = Field(default="Inter")
    font_size: int = Field(default=96, ge=12, le=300)
    font_weight: int = Field(default=700, ge=100, le=900)
    tracking: int = Field(default=15, ge=-100, le=500)
    leading: int = Field(default=110, ge=50, le=250)
    all_caps: bool = False
    fill_color: str = "#ffffff"
    has_stroke: bool = False
    stroke_color: str = "#000000"
    stroke_width: int = Field(default=4, ge=0, le=50)
    stroke_position: Literal["outer", "center", "inner"] = "outer"
    has_shadow: bool = False
    shadow_color: str = "#000000"
    shadow_angle: int = Field(default=135, ge=0, le=360)
    shadow_distance: int = Field(default=8, ge=0, le=100)
    shadow_blur: int = Field(default=16, ge=0, le=100)
    has_background: bool = False
    bg_color: str = "#090a0f"
    bg_opacity: int = Field(default=80, ge=0, le=100)
    bg_padding: int = Field(default=16, ge=0, le=100)
    bg_radius: int = Field(default=8, ge=0, le=50)


class AutoCutoutSettings(BaseModel):
    """Neural/chroma-key background removal, face retouch and masks."""

    auto_cutout_enabled: bool = False
    cutout_model: Literal["birefnet", "rembg-human", "u2net"] = "birefnet"
    stroke_feather: float = Field(default=2.5, ge=0.0, le=20.0)
    invert_cutout: bool = False
    chroma_key_enabled: bool = False
    key_color: str = "#00ff00"
    tolerance: int = Field(default=45, ge=0, le=100)
    softness: int = Field(default=20, ge=0, le=100)
    spill_reduction: int = Field(default=35, ge=0, le=100)
    face_retouch_enabled: bool = False
    skin_smooth: int = Field(default=30, ge=0, le=100)
    skin_brighten: int = Field(default=15, ge=0, le=100)
    eye_brighten: int = Field(default=20, ge=0, le=100)
    mask_shape: MaskShape = MaskShape.NONE
    mask_invert: bool = False


class PhotoLayer(BaseModel):
    """One layer in a composited document (non-destructive)."""

    id: str
    kind: Literal["raster", "text", "adjustment", "vector", "mask"] = "raster"
    name: str
    visible: bool = True
    locked: bool = False
    opacity: int = Field(default=100, ge=0, le=100)
    blend_mode: BlendMode = BlendMode.NORMAL
    asset_url: str | None = None
    text: TextProperties | None = None
    adjustment: dict[str, object] = Field(default_factory=dict)
    x: int = 0
    y: int = 0
    scale: float = Field(default=1.0, ge=0.01, le=20.0)
    rotation: float = Field(default=0.0, ge=-360.0, le=360.0)
    mask: MaskShape = MaskShape.NONE
    group_id: str | None = None


class PhotoDocument(BaseModel):
    """A composited image document: a stack of layers plus page setup."""

    width: int = Field(default=1080, ge=1, le=8192)
    height: int = Field(default=1920, ge=1, le=8192)
    background_color: str = "#00000000"
    layers: list[PhotoLayer] = Field(default_factory=list)
    version: int = Field(default=1, ge=1)


class PhotoLabRequest(BaseModel):
    """Render a ``PhotoDocument`` into an image."""

    document: PhotoDocument
    export_format: Literal["png", "jpeg", "webp"] = "png"

    x: int = Field(ge=0, le=255)
    y: int = Field(ge=0, le=255)


class ToneCurve(BaseModel):
    """A cubic-spline tone curve: luminance or one RGB channel."""

    points: list[ToneCurvePoint] = Field(min_length=2, max_length=16)
    channel: Literal["master", "r", "g", "b"] = "master"


class LevelsConfig(BaseModel):
    """Levels histogram adjustment (input/output plus midtone gamma)."""

    input_black: int = Field(default=0, ge=0, le=255)
    input_white: int = Field(default=255, ge=0, le=255)
    gamma: float = Field(default=1.0, ge=0.1, le=9.9)
    output_black: int = Field(default=0, ge=0, le=255)
    output_white: int = Field(default=255, ge=0, le=255)