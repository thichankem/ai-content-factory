from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from ._helpers import _clamp, _words
from ._specs import _SPECS
from .contracts import DimensionScore, Pack, QuickWin, SeoReport, Signal, Status
from .profiles import (
    _DIMENSION_LABELS,
    PLATFORM_PROFILES,
    SHORTS,
    TIKTOK,
    YOUTUBE,
    PlatformProfile,
)

_BLOCKING_CAP = 45.0


def _status_for(score: float | None) -> Status:
    if score is None:
        return Status.UNKNOWN
    if score >= 0.85:
        return Status.OK
    if score >= 0.55:
        return Status.WARN
    return Status.FAIL


def _grade(score: float) -> str:
    for threshold, letter in ((90, "A+"), (80, "A"), (70, "B"), (60, "C"), (50, "D")):
        if score >= threshold:
            return letter
    return "F"


def _evaluate_specs(pack: Pack, prof: PlatformProfile) -> list[Signal]:
    signals: list[Signal] = []
    for spec in _SPECS[prof.key]:
        score, detail, fix = spec.fn(pack, prof)
        # A blocking spec only caps the score when its own condition says the
        # pack is unusable; otherwise it is just another weighted signal.
        blocking = spec.blocking and (
            spec.blocking_when is None or spec.blocking_when(pack, prof)
        )
        signals.append(
            Signal(
                id=spec.id,
                label=spec.label,
                dimension=spec.dimension,
                weight=spec.weight,
                score=None if score is None else _clamp(float(score)),
                status=_status_for(score),
                detail=detail,
                fix=fix,
                blocking=blocking,
            )
        )
    return signals


def score_pack(pack: Pack, platform: str) -> SeoReport:
    key = platform.strip().lower()
    profile = PLATFORM_PROFILES.get(key)
    if profile is None:
        raise ValueError(f"Unknown platform {platform!r}; use one of {sorted(_SPECS)}.")
    signals = _evaluate_specs(pack, profile)
    dimensions: list[DimensionScore] = []
    measured_weight = 0.0
    total_weight = 0.0
    overall = 0.0
    for dimension_key, dimension_weight in profile.weights.items():
        group = [signal for signal in signals if signal.dimension == dimension_key]
        if not group:
            continue
        available = [signal for signal in group if signal.score is not None]
        group_total = sum(signal.weight for signal in group)
        group_measured = sum(signal.weight for signal in available)
        dimension_score = (
            sum(signal.weight * (signal.score or 0.0) for signal in available)
            / group_measured
            * 100.0
            if group_measured
            else 0.0
        )
        dimensions.append(
            DimensionScore(
                key=dimension_key,
                label=_DIMENSION_LABELS.get(dimension_key, dimension_key),
                weight=dimension_weight,
                score=dimension_score,
                coverage=_clamp(group_measured / group_total) if group_total else 0.0,
                signals=tuple(group),
            )
        )
        overall += dimension_weight * dimension_score
        measured_weight += dimension_weight * (
            (group_measured / group_total) if group_total else 0.0
        )
        total_weight += dimension_weight
    confidence = _clamp(measured_weight / total_weight) if total_weight else 0.0
    blocking = tuple(
        signal
        for signal in signals
        if signal.blocking and signal.score is not None and signal.score < 0.5
    )
    capped = False
    cap_reason: str | None = None
    final = overall
    if blocking:
        capped = overall > _BLOCKING_CAP
        cap_reason = "Blocking faults: " + "; ".join(
            signal.detail for signal in blocking
        )
        final = min(overall, _BLOCKING_CAP)
    quick_wins = _quick_wins(dimensions, profile)
    projected = min(100.0, final + sum(win.points for win in quick_wins[:3]))
    if blocking:
        projected = min(100.0, max(projected, overall))
    metrics = _metrics(pack, profile)
    score = round(final)
    verdict = _verdict(score, confidence, blocking, pack)
    return SeoReport(
        platform=profile.key,
        label=profile.label,
        score=score,
        grade=_grade(float(score)),
        confidence=confidence,
        capped=capped,
        cap_reason=cap_reason,
        dimensions=tuple(dimensions),
        blocking=blocking,
        quick_wins=quick_wins,
        projected_score=round(projected),
        verdict=verdict,
        metrics=metrics,
        notes=_notes(pack, profile, confidence),
    )


def score_platforms(
    pack: Pack, platforms: Iterable[str] = ("youtube", "tiktok")
) -> dict[str, SeoReport]:
    return {platform: score_pack(pack, platform) for platform in platforms}


def _quick_wins(
    dimensions: Sequence[DimensionScore], profile: PlatformProfile
) -> tuple[QuickWin, ...]:
    wins: list[QuickWin] = []
    for dimension in dimensions:
        group_total = sum(signal.weight for signal in dimension.signals)
        if not group_total:
            continue
        for signal in dimension.signals:
            if signal.score is None or signal.fix is None:
                continue
            if signal.score >= 0.85:
                continue
            share = signal.weight / group_total
            points = dimension.weight * share * (1.0 - signal.score) * 100.0
            wins.append(
                QuickWin(
                    signal_id=signal.id,
                    label=signal.label,
                    points=points,
                    fix=signal.fix,
                )
            )
    wins.sort(key=lambda win: win.points, reverse=True)
    return tuple(wins[:8])


def _metrics(pack: Pack, profile: PlatformProfile) -> dict[str, float]:
    metrics: dict[str, float] = {
        "title_chars": float(len(pack.title.strip())),
        "description_chars": float(len(pack.description.strip())),
        "description_words": float(len(_words(pack.description))),
        "script_words": float(len(_words(pack.script))),
        "hashtag_count": float(len([tag for tag in pack.hashtags if tag.strip()])),
        "tag_count": float(len([tag for tag in pack.tags if tag.strip()])),
    }
    if pack.duration_seconds is not None:
        metrics["duration_seconds"] = float(pack.duration_seconds)
    if pack.cuts_per_minute is not None:
        metrics["cuts_per_minute"] = float(pack.cuts_per_minute)
    engagement = pack.engagement
    if engagement is not None and engagement.views > 0:
        views = float(engagement.views)
        metrics["views"] = views
        metrics["like_rate"] = engagement.likes / views
        metrics["share_rate"] = engagement.shares / views
        metrics["comment_rate"] = engagement.comments / views
        ctr = engagement.ctr_pct()
        if ctr is not None:
            metrics["ctr_pct"] = ctr
        ratio = engagement.avd_ratio(pack.duration_seconds)
        if ratio is not None:
            metrics["watch_ratio"] = ratio
    metrics["completion_target"] = profile.completion_target
    return metrics


def _verdict(
    score: int,
    confidence: float,
    blocking: Sequence[Signal],
    pack: Pack,
) -> str:
    if blocking:
        return (
            f"Do not publish yet: {len(blocking)} blocking fault(s) cap the score — "
            f"{blocking[0].detail} Fix those first, everything else is secondary."
        )
    if confidence < 0.6:
        return (
            f"Provisional {score}/100 — only {confidence * 100:.0f}% of the model "
            "could be measured from this pack. Fill the gaps before "
            "trusting the number."
        )
    if score >= 85:
        return (
            f"Ship it: {score}/100 with {confidence * 100:.0f}% coverage. "
            "A/B the thumbnail next."
        )
    if score >= 70:
        return (
            f"Solid ({score}/100). Working the quick wins below projects to "
            f"{score + 1}-{min(100, score + 12)}/100."
        )
    if score >= 55:
        return (
            f"Needs work ({score}/100). Do the top three quick wins before publishing."
        )
    return (
        f"Not ready ({score}/100). Rebuild the pack from the optimiser output "
        "rather than patching it."
    )


def _notes(pack: Pack, profile: PlatformProfile, confidence: float) -> tuple[str, ...]:
    notes: list[str] = [
        f"Model: {len(_SPECS[profile.key])} weighted signals across "
        f"{len(profile.weights)} dimensions "
        "("
        + ", ".join(f"{key} {value:.0%}" for key, value in profile.weights.items())
        + ").",
        "Signals that cannot be measured are excluded and lower confidence "
        f"(current coverage {confidence * 100:.0f}%), so the score never invents data.",
    ]
    if profile.key == "youtube":
        notes.append(
            "YouTube search matches title, description and video content; "
            "hashtags above the title are capped at 3 and every hashtag is "
            "ignored above 60."
        )
    if profile.key == "tiktok":
        notes.append(
            "TikTok indexes the caption, on-screen text and spoken words, and "
            "weights completion and rewatch most; the first 2 seconds decide the rest."
        )
    if pack.engagement is None and not profile.short_form:
        notes.append(
            "No analytics supplied, so watch-time signals are unknown — supply "
            "impressions/views/watch time after publishing to close the loop."
        )
    return tuple(notes)


def platform_rules() -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    for key, profile in (
        ("youtube", YOUTUBE),
        ("youtube_shorts", SHORTS),
        ("tiktok", TIKTOK),
    ):
        rules.append(
            {
                "platform": key,
                "label": profile.label,
                "short_form": profile.short_form,
                "title": {
                    "ideal_chars": list(profile.title_ideal),
                    "hard_max_chars": profile.title_hard_max,
                },
                "description": {
                    "ideal_chars": list(profile.description_ideal_chars),
                    "hard_max_chars": profile.description_hard_max,
                    "ideal_words": profile.description_ideal_words,
                    "keyword_zone_chars": profile.keyword_zone,
                },
                "hashtags": {
                    "ideal": list(profile.hashtag_ideal),
                    "hard_max": profile.hashtag_hard_max,
                },
                "tags": {"ideal": list(profile.tags_ideal)},
                "hook_window_seconds": profile.hook_window,
                "duration": {
                    "ideal_seconds": list(profile.duration_ideal),
                    "hard_max_seconds": profile.duration_hard_max,
                },
                "aspect_required": list(profile.aspect_required),
                "targets": {
                    "completion_rate": profile.completion_target,
                    "watch_ratio": profile.avd_ratio_target,
                    "ctr_pct": profile.ctr_target,
                    "cuts_per_minute_min": profile.cuts_per_minute_min,
                },
                "dimensions": dict(profile.weights),
                "signals": [
                    {
                        "id": spec.id,
                        "label": spec.label,
                        "dimension": spec.dimension,
                        "weight": spec.weight,
                        "blocking": spec.blocking,
                    }
                    for spec in _SPECS[key]
                ],
            }
        )
    return rules
