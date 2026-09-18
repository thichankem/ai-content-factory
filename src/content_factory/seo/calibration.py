from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from ._specs import _SPECS
from .profiles import PLATFORM_PROFILES


@dataclass(frozen=True)
class CalibrationReport:
    platform: str
    observations: int
    outcome: str
    correlations: tuple[dict[str, Any], ...]
    suggested_weights: dict[str, dict[str, float]]
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "observations": self.observations,
            "outcome": self.outcome,
            "correlations": [dict(row) for row in self.correlations],
            "suggested_weights": {
                dimension: dict(weights)
                for dimension, weights in self.suggested_weights.items()
            },
            "notes": list(self.notes),
        }


def _pearson(xs: Sequence[float], ys: Sequence[float]) -> float:
    if len(xs) < 3 or len(xs) != len(ys):
        return 0.0
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=False))
    var_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    var_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if var_x == 0 or var_y == 0:
        return 0.0
    return numerator / (var_x * var_y)


def calibrate(
    observations: Sequence[tuple[dict[str, float], float]],
    platform: str,
    *,
    outcome: str = "views_per_day",
) -> CalibrationReport:
    key = platform.strip().lower()
    profile = PLATFORM_PROFILES.get(key)
    if profile is None:
        raise ValueError(f"Unknown platform {platform!r}.")
    specs = {spec.id: spec for spec in _SPECS[profile.key]}
    outcomes = [value for _, value in observations]
    correlations: list[dict[str, Any]] = []
    strength: dict[str, float] = {}
    for signal_id, spec in specs.items():
        xs = [float(signals.get(signal_id, 0.0)) for signals, _ in observations]
        r = _pearson(xs, outcomes) if observations else 0.0
        correlations.append(
            {
                "signal_id": signal_id,
                "label": spec.label,
                "dimension": spec.dimension,
                "correlation": round(r, 4),
                "observations": len(observations),
            }
        )
        strength[signal_id] = max(0.0, r)
    correlations.sort(key=lambda row: row["correlation"], reverse=True)
    suggested: dict[str, dict[str, float]] = {}
    for dimension in profile.weights:
        group = [
            (spec_id, value)
            for spec_id, value in strength.items()
            if specs[spec_id].dimension == dimension
        ]
        total = sum(value for _, value in group)
        if total <= 0:
            suggested[dimension] = {
                spec_id: specs[spec_id].weight for spec_id, _ in group
            }
            continue
        suggested[dimension] = {
            spec_id: round(value / total, 4) for spec_id, value in group
        }
    notes = [
        "Correlation is measured against the outcome you supply "
        "(views/day, completion, watch time) — not against the platforms' internals.",
    ]
    if len(observations) < 8:
        notes.append(
            f"Only {len(observations)} observation(s): treat these weights as a hint. "
            "Twenty or more published videos per format is the useful threshold."
        )
    if all(row["correlation"] <= 0 for row in correlations) and observations:
        notes.append(
            "No positive correlation found: the sample is too small or the signals "
            "are not measurable in this data. Keep the default weights."
        )
    return CalibrationReport(
        platform=profile.key,
        observations=len(observations),
        outcome=outcome,
        correlations=tuple(correlations),
        suggested_weights=suggested,
        notes=tuple(notes),
    )
