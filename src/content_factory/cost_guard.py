"""Estimate and gate the cost of expensive AI plan steps.

Expensive AI calls (vision, audio LLM, TTS, embeddings, STT) can accumulate
fast during a production run. This module lets the pipeline price a proposed
set of calls up front and decide whether a human confirmation is warranted
before spending money.

  * :func:`estimate_cost` — price a ``{step: call_count}`` map.
  * :func:`should_confirm` — decide whether the estimate crosses a threshold.
  * :class:`CostGuard` — a configurable gate combining both, with an on/off
    switch so the operator can disable confirmation entirely.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CostEstimate:
    """The priced cost of a proposed set of AI calls."""

    total_usd: float
    breakdown: dict[str, float]
    calls: dict[str, int]


UNIT_COSTS_USD: dict[str, float] = {
    "vision": 0.010,
    "audio_llm": 0.020,
    "tts": 0.002,
    "embedding": 0.0001,
    "stt": 0.003,
}


def estimate_cost(
    calls: dict[str, int], unit_costs: dict[str, float] | None = None
) -> CostEstimate:
    """Price ``calls`` using ``unit_costs`` (defaults to :data:`UNIT_COSTS_USD`).

    Steps with no known unit cost contribute zero. The total is rounded to 4
    decimal places.
    """
    costs = unit_costs if unit_costs is not None else UNIT_COSTS_USD
    breakdown: dict[str, float] = {}
    total = 0.0
    for step, count in calls.items():
        cost = costs.get(step, 0.0) * count
        breakdown[step] = cost
        total += cost
    return CostEstimate(
        total_usd=round(total, 4),
        breakdown=breakdown,
        calls=dict(calls),
    )


def should_confirm(estimate: CostEstimate, threshold_usd: float) -> bool:
    """True when the estimate exceeds ``threshold_usd`` (strictly)."""
    return estimate.total_usd > threshold_usd


@dataclass(frozen=True)
class PlanBudget:
    """Budget configuration controlling the cost gate."""

    enabled: bool
    threshold_usd: float
    unit_costs: dict[str, float]


class CostGuard:
    """Gate a proposed plan's cost behind a configurable confirmation check."""

    def __init__(self, budget: PlanBudget) -> None:
        self._budget = budget

    def check(self, calls: dict[str, int]) -> tuple[CostEstimate, bool]:
        """Return ``(estimate, needs_confirmation)`` for ``calls``.

        When the budget is disabled, ``needs_confirmation`` is always False.
        """
        estimate = estimate_cost(calls, self._budget.unit_costs)
        needs_confirmation = self._budget.enabled and should_confirm(
            estimate, self._budget.threshold_usd
        )
        return estimate, needs_confirmation
