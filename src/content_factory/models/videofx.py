"""Video FX models: speed ramping, Bézier keyframes and colour.

Mirrors ``docs/SPEC-VIDEO-EDITING.md``. Two ideas the rest of the backend leans
on live here:

* a keyframe carries its own easing, so one clip can mix linear, hold and Bézier
  segments without the caller re-deriving them;
* a speed ramp is a *list of points*, not a multiplier, because a ramp that
  cannot describe "slow, fast, slow" is not a ramp.
"""

from __future__ import annotations

import enum
from typing import Literal

from pydantic import BaseModel, Field


class BezierHandle(BaseModel):
    """One control handle of a cubic Bézier easing segment."""

    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=-1.0, le=2.0)


class BezierKeyframe(BaseModel):
    """A keyframe with incoming/outgoing easing and an interpolation mode."""

    time: float = Field(ge=0.0)
    value: float
    ease_in: BezierHandle = Field(default_factory=lambda: BezierHandle(x=0.42, y=0.0))
    ease_out: BezierHandle = Field(default_factory=lambda: BezierHandle(x=0.58, y=1.0))
    interpolation: Literal["linear", "bezier", "hold"] = "bezier"


class EasePreset(enum.StrEnum):
    """Named easing curves an editor can pick without drawing handles."""

    LINEAR = "linear"
    EASE_IN = "ease-in"
    EASE_OUT = "ease-out"
    EASY_EASE = "easy-ease"
    EXPONENTIAL_POP = "exponential-pop"
    RUBBER_BAND = "rubber-band"


class SpeedRampPoint(BaseModel):
    """One point of a speed ramp: a fraction of the clip and its speed."""

    time_offset: float = Field(ge=0.0, le=1.0)
    speed_factor: float = Field(ge=0.1, le=10.0)
    easing: EasePreset = EasePreset.EASE_IN


class FrameInterpolation(enum.StrEnum):
    """How in-between frames are produced when time is remapped."""

    OPTICAL_FLOW = "optical-flow"
    FRAME_BLEND = "frame-blend"
    NEAREST_NEIGHBOUR = "nearest-neighbour"


class SpeedRampConfig(BaseModel):
    """A non-linear speed change applied to one scene."""

    scene_id: str
    points: list[SpeedRampPoint] = Field(min_length=2, max_length=16)
    interpolation: FrameInterpolation = FrameInterpolation.FRAME_BLEND
    preserve_pitch: bool = True


class LumetriColorConfig(BaseModel):
    """Primary colour controls plus an optional cinematic LUT."""

    lut: Literal[
        "none",
        "teal-orange",
        "cyberpunk-neon",
        "film-noir-1940",
        "kodachrome-64",
        "matrix-emerald",
    ] = "none"
    temperature: float = Field(default=0.0, ge=-50.0, le=50.0)
    tint: float = Field(default=0.0, ge=-50.0, le=50.0)
    exposure_ev: float = Field(default=0.0, ge=-5.0, le=5.0)
    contrast: float = Field(default=0.0, ge=-100.0, le=100.0)
    saturation: float = Field(default=0.0, ge=-100.0, le=100.0)
    highlights: float = Field(default=0.0, ge=-100.0, le=100.0)
    shadows: float = Field(default=0.0, ge=-100.0, le=100.0)


class SafeZoneSpec(BaseModel):
    """The 9:16 UI exclusion margins a caption must stay inside."""

    title_safe_percent: float = Field(default=80.0, ge=50.0, le=100.0)
    action_safe_percent: float = Field(default=90.0, ge=50.0, le=100.0)
    top_percent: float = Field(default=15.0, ge=0.0, le=50.0)
    bottom_percent: float = Field(default=22.0, ge=0.0, le=50.0)
    right_percent: float = Field(default=15.0, ge=0.0, le=50.0)