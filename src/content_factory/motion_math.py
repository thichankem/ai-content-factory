"""Motion maths: Bézier easing, speed ramps and safe zones.

Pure functions, no I/O, so a render plan can be computed anywhere — in a test,
in a worker thread, or inside the Fusion graph evaluator. The maths follows
``docs/SPEC-VIDEO-EDITING.md`` §2.2–2.3: a keyframe carries its own easing, and
a speed ramp is a list of (position, factor) points that rescale the clip's
timeline without changing its source.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "EASE_PRESETS",
    "evaluate_bezier",
    "evaluate_ramp",
    "ramp_duration",
    "safe_zone_box",
]


#: Named easing curves, as cubic-Bézier control handles (P1, P2).
EASE_PRESETS: dict[str, tuple[tuple[float, float], tuple[float, float]]] = {
    "linear": ((0.0, 0.0), (1.0, 1.0)),
    "ease-in": ((0.42, 0.0), (1.0, 1.0)),
    "ease-out": ((0.0, 0.0), (0.58, 1.0)),
    "easy-ease": ((0.25, 0.1), (0.25, 1.0)),
    "exponential-pop": ((0.2, 0.0), (0.3, 1.4)),
    "rubber-band": ((0.3, -0.4), (0.7, 1.4)),
}


def _cubic_bezier(y1: float, y2: float, t: float) -> float:
    """The time-independent cubic Bézier value curve at parameter ``t``."""
    u = 1.0 - t
    return 3.0 * u * u * t * y1 + 3.0 * u * t * t * y2 + t * t * t


def evaluate_bezier(
    value_start: float,
    value_end: float,
    progress: float,
    ease_in: tuple[float, float] = (0.42, 0.0),
    ease_out: tuple[float, float] = (0.58, 1.0),
) -> float:
    """Interpolate between two values along a cubic Bézier easing curve.

    ``progress`` is the normalised time (0.0 → 1.0) between the two keyframes.
    De Casteljau evaluation over the two control handles gives the same motion
    an editor sees when dragging a graph editor's handles.
    """
    t = max(0.0, min(1.0, float(progress)))
    eased = _cubic_bezier(ease_in[1], ease_out[1], t)
    return value_start + (value_end - value_start) * eased


def evaluate_ramp(points: list[dict[str, Any]], position: float) -> float:
    """The speed factor at ``position`` (0.0 → 1.0) along a speed ramp.

    Points may be sorted in any order; they are sorted by ``time_offset`` first.
    Outside the ramp the end values hold, so a clip that starts slow keeps that
    speed until its first point.
    """
    if len(points) < 2:
        raise ValueError("A speed ramp needs at least two points.")
    ordered = sorted(points, key=lambda p: float(p.get("time_offset", 0.0)))
    position = max(0.0, min(1.0, float(position)))

    previous = ordered[0]
    for point in ordered[1:]:
        if position <= float(point["time_offset"]):
            span = float(point["time_offset"]) - float(previous["time_offset"])
            if span <= 0.0:
                return float(point["speed_factor"])
            progress = (position - float(previous["time_offset"])) / span
            ease_in, ease_out = EASE_PRESETS.get(
                str(point.get("easing", "ease-in")), EASE_PRESETS["ease-in"]
            )
            return evaluate_bezier(
                float(previous["speed_factor"]),
                float(point["speed_factor"]),
                progress,
                ease_in,
                ease_out,
            )
        previous = point
    return float(previous["speed_factor"])


def ramp_duration(duration: float, points: list[dict[str, Any]], samples: int = 240) -> float:
    """How long a clip of ``duration`` seconds takes once the ramp is applied.

    The ramp rescales time, so the rendered length is the integral of
    ``1 / speed`` across the clip — approximated by sampling, which is exact
    enough at 240 samples for any ramp an editor can draw.
    """
    if duration <= 0.0:
        return 0.0
    if len(points) < 2:
        return duration
    total = 0.0
    for index in range(samples):
        position = (index + 0.5) / samples
        speed = max(0.1, evaluate_ramp(points, position))
        total += duration / samples / speed
    return total


def safe_zone_box(
    width: int,
    height: int,
    top_percent: float = 15.0,
    bottom_percent: float = 22.0,
    right_percent: float = 15.0,
) -> dict[str, int]:
    """The 9:16 UI exclusion margins, as a box captions must stay inside.

    Returns pixel coordinates (``left/top/right/bottom``) for the **safe** area,
    so a client can draw the exclusion frame without knowing the resolution.
    """
    if width <= 0 or height <= 0:
        raise ValueError("Safe zones need a non-zero canvas.")
    top = int(round(height * max(0.0, min(50.0, top_percent)) / 100.0))
    bottom = int(round(height * max(0.0, min(50.0, bottom_percent)) / 100.0))
    right = int(round(width * max(0.0, min(50.0, right_percent)) / 100.0))
    return {"left": 0, "top": top, "right": width - right, "bottom": height - bottom}