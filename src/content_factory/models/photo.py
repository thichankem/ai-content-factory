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