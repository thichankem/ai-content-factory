from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

_METRIC_KEYS: dict[str, str] = {
    "ctr": "clicks/impressions",
    "view_rate": "views/impressions",
    "completion": "completions/views",
    "save_rate": "saves/views",
    "share_rate": "shares/views",
    "follow_rate": "follows/views",
}
_CONTINUOUS_METRICS = frozenset({"avd", "watch_time_per_view"})
METRIC_NAMES: tuple[str, ...] = tuple(sorted({*_METRIC_KEYS, *_CONTINUOUS_METRICS}))


@dataclass(frozen=True)
class AbArm:
    name: str
    impressions: int = 0
    clicks: int = 0
    views: int = 0
    completions: int = 0
    saves: int = 0
    shares: int = 0
    follows: int = 0
    watch_time_seconds: float = 0.0
    mean_value: float | None = None
    sd_value: float | None = None

    def rate(self, metric: str) -> float | None:
        if metric in _CONTINUOUS_METRICS:
            if self.mean_value is not None:
                return self.mean_value
            if self.views > 0 and self.watch_time_seconds > 0:
                return self.watch_time_seconds / self.views
            return None
        numerator, denominator = _METRIC_KEYS[metric].split("/")
        top = float(getattr(self, numerator))
        bottom = float(getattr(self, denominator))
        if bottom <= 0:
            return None
        return top / bottom

    def sample_size(self, metric: str) -> int:
        if metric in _CONTINUOUS_METRICS:
            return int(self.views)
        _, denominator = _METRIC_KEYS[metric].split("/")
        return int(getattr(self, denominator))


def _z_for_confidence(confidence: float) -> float:
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")
    p = 1.0 - (1.0 - confidence) / 2.0
    a = (
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577518672690e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    )
    b = (
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    )
    c = (
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    )
    d = (
        7.784695709041462e-03,
        3.224671290700398e-01,
        2.445134137142996e00,
        3.754408661907416e00,
    )
    plow = 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1
        )
    if p > 1 - plow:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(
            (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5])
            / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
        )
    q = p - 0.5
    r = q * q
    return (
        (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5])
        * q
        / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)
    )


def _normal_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _wilson(
    successes: int, trials: int, confidence: float = 0.95
) -> tuple[float, float]:
    if trials <= 0:
        return 0.0, 0.0
    z = _z_for_confidence(confidence)
    phat = successes / trials
    denominator = 1 + z * z / trials
    centre = (phat + z * z / (2 * trials)) / denominator
    spread = (
        z * math.sqrt(phat * (1 - phat) / trials + z * z / (4 * trials * trials))
    ) / denominator
    return max(0.0, centre - spread), min(1.0, centre + spread)


@dataclass(frozen=True)
class AbPlan:
    metric: str
    baseline_rate: float
    target_rate: float
    relative_lift: float
    per_arm: int
    total: int
    daily_traffic: int | None
    days: int | None
    alpha: float
    power: float
    variables_to_hold: tuple[str, ...]
    decision_rule: str
    read_metric: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric,
            "baseline_rate": round(self.baseline_rate, 5),
            "target_rate": round(self.target_rate, 5),
            "relative_lift": round(self.relative_lift, 4),
            "per_arm": self.per_arm,
            "total": self.total,
            "daily_traffic": self.daily_traffic,
            "days": self.days,
            "alpha": self.alpha,
            "power": self.power,
            "variables_to_hold": list(self.variables_to_hold),
            "decision_rule": self.decision_rule,
            "read_metric": self.read_metric,
        }


def plan_ab_test(
    metric: str,
    baseline_rate: float,
    *,
    relative_lift: float = 0.15,
    daily_traffic: int | None = None,
    arms: int = 2,
    alpha: float = 0.05,
    power: float = 0.8,
) -> AbPlan:
    key = metric.strip().lower()
    if key not in _METRIC_KEYS and key not in _CONTINUOUS_METRICS:
        raise ValueError(
            f"Unknown metric {metric!r}; use "
            f"{sorted([*_METRIC_KEYS, *_CONTINUOUS_METRICS])}."
        )
    if not 0 < baseline_rate < 1:
        raise ValueError("baseline_rate must be a rate between 0 and 1")
    target = min(0.999, baseline_rate * (1.0 + relative_lift))
    z_alpha = _z_for_confidence(1 - alpha)
    z_beta = _z_for_confidence(1 - (1 - power) * 2) if power < 1 else 1.2816
    pooled = (baseline_rate + target) / 2.0
    variance = baseline_rate * (1 - baseline_rate) + target * (1 - target)
    effect = target - baseline_rate
    per_arm = math.ceil(
        (
            (
                z_alpha * math.sqrt(2 * pooled * (1 - pooled))
                + z_beta * math.sqrt(variance)
            )
            ** 2
        )
        / (effect**2)
    )
    days = math.ceil(per_arm * arms / daily_traffic) if daily_traffic else None
    hold = (
        ("posting hour", "audience segment", "video length", "sound", "first frame")
        if key in {"ctr", "view_rate"}
        else ("title", "thumbnail", "posting hour", "audience segment")
    )
    rule = (
        f"Declare a winner when each arm has at least {per_arm} observations and "
        f"the two-sided p-value is below {alpha}; otherwise keep the control."
    )
    read_metric = {
        "ctr": "impressions CTR (clicks / impressions) — not views",
        "view_rate": "views / impressions from the For You or browse feed",
        "completion": "completed views / views",
        "save_rate": "saves / views (strongest TikTok distribution signal)",
        "share_rate": "shares / views",
        "follow_rate": "follows / views",
        "avd": "average view duration in seconds (per view)",
        "watch_time_per_view": "total watch time / views",
    }[key]
    return AbPlan(
        metric=key,
        baseline_rate=baseline_rate,
        target_rate=target,
        relative_lift=relative_lift,
        per_arm=per_arm,
        total=per_arm * arms,
        daily_traffic=daily_traffic,
        days=days,
        alpha=alpha,
        power=power,
        variables_to_hold=hold,
        decision_rule=rule,
        read_metric=read_metric,
    )


@dataclass(frozen=True)
class AbEvaluation:
    metric: str
    arms: tuple[dict[str, Any], ...]
    winner: str | None
    verdict: str
    p_value: float
    z_score: float
    lift: float
    lift_relative: float
    observations: int
    required_per_arm: int
    next_step: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric,
            "arms": list(self.arms),
            "winner": self.winner,
            "verdict": self.verdict,
            "p_value": round(self.p_value, 5),
            "z_score": round(self.z_score, 4),
            "lift": round(self.lift, 5),
            "lift_relative": round(self.lift_relative, 4),
            "observations": self.observations,
            "required_per_arm": self.required_per_arm,
            "next_step": self.next_step,
        }


def evaluate_ab_test(
    arms: Sequence[AbArm],
    metric: str,
    *,
    alpha: float = 0.05,
    relative_lift: float = 0.15,
) -> AbEvaluation:
    key = metric.strip().lower()
    if key not in _METRIC_KEYS and key not in _CONTINUOUS_METRICS:
        raise ValueError(f"Unknown metric {metric!r}.")
    if len(arms) < 2:
        raise ValueError("At least two arms are required to compare.")
    rows: list[dict[str, Any]] = []
    for arm in arms:
        rate = arm.rate(key)
        size = arm.sample_size(key)
        successes = round(rate * size) if rate is not None else 0
        low, high = _wilson(successes, size) if rate is not None else (0.0, 0.0)
        rows.append(
            {
                "name": arm.name,
                "observations": size,
                "rate": None if rate is None else round(rate, 5),
                "ci_low": round(low, 5),
                "ci_high": round(high, 5),
                "improvement_vs_control": None,
            }
        )
    control = arms[0]
    control_rate = control.rate(key)
    if control_rate is None or control_rate <= 0:
        return AbEvaluation(
            metric=key,
            arms=tuple(rows),
            winner=None,
            verdict="insufficient_data",
            p_value=1.0,
            z_score=0.0,
            lift=0.0,
            lift_relative=0.0,
            observations=sum(row["observations"] for row in rows),
            required_per_arm=0,
            next_step="The control arm has no measurable rate yet; collect data first.",
        )
    best = control
    best_rate = control_rate
    for arm in arms[1:]:
        rate = arm.rate(key)
        if rate is not None and rate > best_rate:
            best, best_rate = arm, rate
    lift = best_rate - control_rate
    lift_relative = lift / control_rate
    row_by_name = {row["name"]: row for row in rows}
    row_by_name[best.name]["improvement_vs_control"] = round(lift_relative, 4)
    plan = plan_ab_test(
        key,
        min(0.999, max(1e-6, control_rate)),
        relative_lift=relative_lift,
        arms=len(arms),
        alpha=alpha,
    )
    observations = sum(row["observations"] or 0 for row in rows)
    z = 0.0
    p_value = 1.0
    if key in _CONTINUOUS_METRICS and best.sd_value and control.sd_value:
        size_a = max(1, control.sample_size(key))
        size_b = max(1, best.sample_size(key))
        se = math.sqrt(control.sd_value**2 / size_a + best.sd_value**2 / size_b)
        z = lift / se if se > 0 else 0.0
        p_value = 2 * (1 - _normal_cdf(abs(z)))
        test_name = "Welch t-test"
    elif key in _CONTINUOUS_METRICS:
        test_name = "difference of means (no variance supplied)"
        p_value = 1.0
    else:
        numerator, denominator = _METRIC_KEYS[key].split("/")
        n1 = float(getattr(control, denominator))
        n2 = float(getattr(best, denominator))
        c1 = float(getattr(control, numerator))
        c2 = float(getattr(best, numerator))
        if n1 <= 0 or n2 <= 0:
            return AbEvaluation(
                metric=key,
                arms=tuple(rows),
                winner=None,
                verdict="insufficient_data",
                p_value=1.0,
                z_score=0.0,
                lift=lift,
                lift_relative=lift_relative,
                observations=int(observations),
                required_per_arm=plan.per_arm,
                next_step="One arm has no exposures yet.",
            )
        pooled = (c1 + c2) / (n1 + n2)
        se = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
        z = (c2 / n2 - c1 / n1) / se if se > 0 else 0.0
        p_value = 2 * (1 - _normal_cdf(abs(z)))
        test_name = "pooled two-proportion z-test"
    smallest = min(int(row["observations"] or 0) for row in rows)
    if smallest < plan.per_arm:
        verdict = "keep_running"
        winner = None
        next_step = (
            f"Only {smallest} of the {plan.per_arm} observations per arm are in. "
            f"Run on ({plan.decision_rule})"
        )
    elif p_value < alpha:
        winner = best.name
        verdict = "winner"
        next_step = (
            f"{best.name} beats {control.name} by {lift_relative * 100:.1f}% "
            f"(p={p_value:.4f}, {test_name}). Roll it out and test the next variable: "
            "thumbnail, then hook."
        )
    else:
        winner = None
        verdict = "no_difference"
        next_step = (
            f"No detectable difference after {smallest} observations per arm "
            f"(p={p_value:.4f}). Either accept the control or raise the effect you "
            "test for — try a bolder variant rather than a tweak."
        )
    return AbEvaluation(
        metric=key,
        arms=tuple(rows),
        winner=winner,
        verdict=verdict,
        p_value=p_value,
        z_score=z,
        lift=lift,
        lift_relative=lift_relative,
        observations=int(observations),
        required_per_arm=plan.per_arm,
        next_step=next_step,
    )
