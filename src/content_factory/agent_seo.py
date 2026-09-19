"""SEO agent tools: score it, fix it, and prove the fix.

Split out of ``agent_tools.py`` so the registry module holds only the assembly
of the manifest, while the SEO domain keeps its handlers next to the schemas
that describe them.
"""

from __future__ import annotations

from typing import Any

from .agent_schema import (
    _CALIBRATION_PLATFORMS,
    _METRIC,
    _PLATFORM,
    PACK,
    PROJECT,
    Args,
    ToolError,
    ToolSpec,
    _p,
)
from .models import SEO_METRICS, SEO_PLATFORMS

# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


def _optional_int(args: Args, key: str) -> int | None:
    """Read an optional whole number, tolerating a float from JSON."""
    value = args.number(key)
    return None if value is None else int(value)


def _h_seo_rules(service: Any, args: Args) -> Any:
    """Every threshold and signal weight the scorer uses, per platform."""
    return service.seo_rules()


def _h_seo_score(service: Any, args: Args) -> Any:
    """Score one publish pack, optionally on every platform at once."""
    return service.seo_score(
        args.choice("platform", SEO_PLATFORMS, "youtube"), args.mapping("pack")
    )


def _h_seo_optimize(service: Any, args: Args) -> Any:
    """Rewrite the pack for the best measurable score and report the gain."""
    return service.seo_optimize(
        args.choice("platform", SEO_PLATFORMS, "youtube"), args.mapping("pack")
    )


def _h_seo_score_project(service: Any, args: Args) -> Any:
    """Score what a stored project would actually publish, not a hypothetical."""
    return service.seo_score_project(
        args.ident("project_id"),
        args.choice("platform", SEO_PLATFORMS, "youtube"),
        keywords=args.strings("keywords") or None,
        publish_hour=_optional_int(args, "publish_hour"),
        audience_hours=[int(hour) for hour in args.numbers("audience_hours")],
        description=args.optional_string("description"),
        tags=args.strings("tags"),
        hashtags=args.strings("hashtags"),
        title=args.optional_string("title"),
        engagement=args.mapping("engagement") or None,
    )


def _h_seo_ab_plan(service: Any, args: Args) -> Any:
    """Size an A/B test: how much traffic a real decision needs."""
    return service.seo_ab_plan(
        args.choice("metric", SEO_METRICS, "ctr"),
        args.number_or("baseline_rate", 0.04),
        relative_lift=args.number_or("relative_lift", 0.15),
        daily_traffic=_optional_int(args, "daily_traffic"),
        arms=args.integer("arms", 2),
        alpha=args.number_or("alpha", 0.05),
        power=args.number_or("power", 0.8),
    )


def _h_seo_ab_evaluate(service: Any, args: Args) -> Any:
    """Decide whether a variant really beat the control, or it was noise."""
    arms = args.objects("arms")
    if len(arms) < 2:
        raise ToolError("Argument 'arms' needs at least two variants to compare.")
    return service.seo_ab_evaluate(
        args.choice("metric", SEO_METRICS, "ctr"),
        arms,
        alpha=args.number_or("alpha", 0.05),
        relative_lift=args.number_or("relative_lift", 0.15),
    )


def _h_seo_keywords(service: Any, args: Args) -> Any:
    """Rank phrases by demand vs competition and mine winning phrasings."""
    keywords = args.strings("keywords")
    if not keywords:
        raise ToolError("Argument 'keywords' needs at least one phrase.")
    return service.seo_keywords(
        keywords, args.objects("competitors"), pack=args.mapping("pack") or None
    )


def _h_seo_calibrate(service: Any, args: Args) -> Any:
    """Learn which signals actually predict this channel's outcomes."""
    observations = [
        (dict(row.get("signals") or {}), float(row.get("outcome") or 0.0))
        for row in args.objects("observations")
    ]
    return service.seo_calibrate(
        observations,
        args.choice("platform", _CALIBRATION_PLATFORMS, "youtube"),
        outcome=args.string("outcome", "views_per_day"),
    )


# ---------------------------------------------------------------------------
# Specs
# ---------------------------------------------------------------------------

SEO_SPECS: list[ToolSpec] = [
    ToolSpec(
        "seo_rules",
        "Every platform threshold and signal weight the SEO scorer uses, so an "
        "agent reasons from the same numbers instead of guessing at them.",
        "seo",
        "seo_rules",
        _h_seo_rules,
    ),
    ToolSpec(
        "seo_score",
        "Score a publish pack 0-100 for youtube, youtube_shorts, tiktok or all: "
        "blocking issues, per-dimension breakdown, quick wins and confidence.",
        "seo",
        "seo_score",
        _h_seo_score,
        {"platform": _PLATFORM, "pack": PACK},
        ("pack",),
    ),
    ToolSpec(
        "seo_optimize",
        "Rewrite a pack for the maximum score and return the measured gain, so "
        "the fix is verified rather than assumed.",
        "seo",
        "seo_optimize",
        _h_seo_optimize,
        {"platform": _PLATFORM, "pack": PACK},
        ("pack",),
    ),
    ToolSpec(
        "seo_score_project",
        "Score what a stored project would actually publish: hook from the "
        "script, runtime, aspect, caption state, chapters, cut rate and audio.",
        "seo",
        "seo_score_project",
        _h_seo_score_project,
        {
            "project_id": PROJECT,
            "platform": _PLATFORM,
            "keywords": _p("array", "Target phrases, first one is primary."),
            "title": _p("string", "Override the project title."),
            "description": _p("string", "Override the description."),
            "tags": _p("array", "Tag list to score."),
            "hashtags": _p("array", "Hashtag list to score."),
            "publish_hour": _p("integer", "Planned local publish hour 0-23."),
            "audience_hours": _p("array", "Hours your audience is active."),
            "engagement": _p(
                "object",
                "Real metrics once published: views, impressions, likes, "
                "comments, shares, saves, follows, watch_time_seconds, "
                "average_view_seconds, completion_rate.",
            ),
        },
        ("project_id",),
    ),
    ToolSpec(
        "seo_ab_plan",
        "Size an A/B test for a detectable lift: sample per arm, calendar days "
        "at your traffic, and the decision rule.",
        "seo",
        "seo_ab_plan",
        _h_seo_ab_plan,
        {
            "metric": _METRIC,
            "baseline_rate": _p("number", "Current rate, e.g. 0.04 for 4% CTR."),
            "relative_lift": _p("number", "Lift to detect, 0.15 = +15%."),
            "daily_traffic": _p("integer", "Impressions/views per day available."),
            "arms": _p("integer", "Number of variants 2-6."),
            "alpha": _p("number", "Significance level, default 0.05."),
            "power": _p("number", "Power, default 0.8."),
        },
        ("baseline_rate",),
    ),
    ToolSpec(
        "seo_ab_evaluate",
        "Test whether a variant really beat the control: p-value, confidence "
        "interval, lift and a ship/keep-testing verdict.",
        "seo",
        "seo_ab_evaluate",
        _h_seo_ab_evaluate,
        {
            "metric": _METRIC,
            "arms": _p(
                "array",
                "2+ arms: name, impressions, clicks, views, completions, saves, "
                "shares, follows, watch_time_seconds, mean_value, sd_value.",
            ),
            "alpha": _p("number", "Significance level, default 0.05."),
            "relative_lift": _p("number", "Lift you would act on."),
        },
        ("arms",),
    ),
    ToolSpec(
        "seo_keywords",
        "Rank phrases by demand versus competition and mine the winning "
        "phrasings, using an optional competitor corpus.",
        "seo",
        "seo_keywords",
        _h_seo_keywords,
        {
            "keywords": _p("array", "Candidate phrases to rank."),
            "competitors": _p(
                "array",
                "Niche corpus rows: title, views, channel, subscribers, "
                "days_old, duration_seconds.",
            ),
            "pack": PACK,
        },
        ("keywords",),
    ),
    ToolSpec(
        "seo_calibrate",
        "Correlate each signal with this channel's real outcomes and suggest "
        "weights fitted to your own data instead of generic averages.",
        "seo",
        "seo_calibrate",
        _h_seo_calibrate,
        {
            "observations": _p("array", "Rows of {signals: {...}, outcome: number}."),
            "platform": _p(
                "string",
                "youtube, youtube_shorts or tiktok.",
                enum=list(_CALIBRATION_PLATFORMS),
                default="youtube",
            ),
            "outcome": _p("string", "What you are predicting."),
        },
        ("observations",),
    ),
]
