from __future__ import annotations

import hashlib
import json
from dataclasses import FrozenInstanceError
from importlib import import_module
from pathlib import Path

import pytest

from content_factory import seo


def representative_pack() -> seo.Pack:
    return seo.Pack(
        title="Điện Biên Phủ: 5 facts that changed history",
        description="Điện Biên Phủ explained with archive evidence. Why did it matter?",
        tags=("Điện Biên Phủ", "history explained"),
        hashtags=("#history", "#fyp", "#DienBienPhu"),
        keywords=("Điện Biên Phủ", "history", "archive evidence"),
        script="Điện Biên Phủ changed history. Here are 5 facts. Follow for evidence.",
        hook="5 facts about Điện Biên Phủ",
        duration_seconds=30.0,
        aspect_ratio="9:16",
        thumbnail_present=True,
        thumbnail_text="The turning point",
        on_screen_text=("Điện Biên Phủ", "Archive evidence"),
        has_captions=True,
        caption_source="manual",
        has_chapters=False,
        chapter_count=0,
        has_end_screen=False,
        playlist="history",
        sound="original",
        sound_trending=False,
        beat_synced=True,
        bpm=120,
        cuts_per_minute=18.0,
        loop_friendly=False,
        intro_seconds=0.0,
        text_in_safe_zone=True,
        publish_hour=19,
        audience_hours=(21, 19),
        watermark=False,
        comment_prompt=False,
        series_part=2,
        duet_stitch_enabled=True,
        channel="archive",
        language="en",
        engagement=seo.Engagement(
            impressions=10000,
            views=500,
            likes=25,
            comments=10,
            shares=8,
            saves=4,
            follows=3,
            watch_time_seconds=10000,
            average_view_seconds=20,
            completion_rate=0.6,
        ),
    )


def engine_snapshot() -> dict:
    pack = representative_pack()
    competitors = [
        seo.CompetitorVideo("Điện Biên Phủ history", 10000, "archive", 1000, 10),
        seo.CompetitorVideo("Điện Biên Phủ explained", 20000, "history", 2000, 0),
        seo.CompetitorVideo("History explained", 5000, "archive", 1000, 90),
        seo.CompetitorVideo("History explained again", 30000, "archive", 1000, None),
    ]
    observations = [
        ({"hook": index / 10, "title_keyword": (10 - index) / 10}, float(index))
        for index in range(10)
    ]
    arms = [
        seo.AbArm("control", impressions=100000, clicks=4000, views=10000),
        seo.AbArm("variant", impressions=100000, clicks=6000, views=14000),
        seo.AbArm("third", impressions=100000, clicks=5000, views=12000),
    ]
    continuous = [
        seo.AbArm("control", views=10000, mean_value=0.4, sd_value=0.1),
        seo.AbArm("variant", views=10000, mean_value=0.5, sd_value=0.1),
    ]
    return {
        "rules": seo.platform_rules(),
        "scores": [
            seo.score_pack(candidate, platform).to_dict()
            for candidate in (
                seo.Pack(),
                pack,
                pack.with_changes(
                    title="X" * 150,
                    duration_seconds=50000,
                    watermark=True,
                    hashtags=tuple(f"#tag{i}" for i in range(65)),
                    aspect_ratio="1:1",
                ),
            )
            for platform in ("youtube", "youtube_shorts", "tiktok", " SHORTS ")
        ],
        "optimizations": [
            seo.optimize_pack(candidate, platform).to_dict()
            for candidate in (seo.Pack(), pack, pack.with_changes(language="vi"))
            for platform in ("youtube", "youtube_shorts", "tiktok")
        ],
        "keywords": seo.keyword_opportunities(
            ("Điện Biên Phủ", "history", "missing", " "), competitors, pack=pack
        ).to_dict(),
        "keywords_empty": seo.keyword_opportunities(("missing",), ()).to_dict(),
        "calibration": [
            seo.calibrate(rows, platform).to_dict()
            for rows in ([], observations, [({}, 1.0)] * 3)
            for platform in ("youtube", "shorts", "tiktok")
        ],
        "plans": [
            seo.plan_ab_test(metric, 0.04, daily_traffic=1000).to_dict()
            for metric in seo.METRIC_NAMES
        ],
        "evaluations": [
            seo.evaluate_ab_test(candidates, metric).to_dict()
            for candidates, metric in (
                (arms, "ctr"),
                (arms, "view_rate"),
                ([seo.AbArm("a"), seo.AbArm("b")], "ctr"),
                (continuous, "avd"),
                (
                    [
                        seo.AbArm("a", views=20, mean_value=0.3),
                        seo.AbArm("b", views=20, mean_value=0.4),
                    ],
                    "watch_time_per_view",
                ),
            )
        ],
    }


def test_engine_deterministic_baseline() -> None:
    snapshot = engine_snapshot()
    encoded = json.dumps(snapshot, ensure_ascii=False, sort_keys=True).encode()
    assert (
        hashlib.sha256(encoded).hexdigest()
        == "a1bad2606cde1031d77ff4837cb183a60f91a42a7b92c52d0d165326099867c4"
    )
    assert snapshot == engine_snapshot()


def test_only_unusable_packs_are_capped() -> None:
    """A short title or a 4-minute runtime is advice, not a publish blocker."""
    short = representative_pack().with_changes(
        title="Titanic", duration_seconds=240.0, hashtags=()
    )
    report = seo.score_pack(short, "youtube")
    blocked = {signal.id for signal in report.blocking}
    assert not {"title_length", "duration_fit", "hashtags"} & blocked
    assert not report.capped
    assert report.score > 45

    broken = short.with_changes(title="", hashtags=())
    blocked = {signal.id for signal in seo.score_pack(broken, "youtube").blocking}
    assert "title_length" in blocked
    assert seo.score_pack(broken, "youtube").capped


def test_optimizer_gain_is_measured_not_claimed() -> None:
    """Every optimiser run must reproduce its own promised score."""
    for pack, platform in (
        (seo.Pack(), "youtube"),
        (seo.Pack(), "tiktok"),
        (representative_pack(), "youtube_shorts"),
    ):
        plan = seo.optimize_pack(pack, platform)
        assert plan.gain >= 0
        rebuilt = pack.with_changes(
            title=plan.title,
            description=plan.description,
            hashtags=plan.hashtags,
            tags=plan.tags,
            hook=plan.hook,
            comment_prompt=plan.comment_prompt,
        )
        assert seo.score_pack(rebuilt, platform).score == plan.after.score
        if plan.changes:
            assert plan.gain > 0, "a listed change must have moved the score"


def test_optimizer_fills_the_platform_bands() -> None:
    pack = seo.Pack(
        title="Tàu Titanic",
        description="Chuyện con tàu.",
        keywords=("tàu titanic",),
        hook="Con tàu này được cho là không thể chìm.",
    )
    plan = seo.optimize_pack(pack, "youtube")
    low, high = seo.YOUTUBE.title_ideal
    assert low <= len(plan.title) <= high
    assert len(plan.hashtags) == seo.YOUTUBE.hashtag_ideal[1]
    assert len(plan.tags) >= seo.YOUTUBE.tags_ideal[0]


def test_alias_and_default_platforms() -> None:
    pack = representative_pack()
    assert seo.score_pack(pack, " SHORTS ") == seo.score_pack(pack, "youtube_shorts")
    assert tuple(seo.score_platforms(pack)) == ("youtube", "tiktok")
    assert seo.PLATFORM_PROFILES["shorts"] is seo.SHORTS
    with pytest.raises(ValueError, match="Unknown platform"):
        seo.score_pack(pack, "unknown")


def test_pack_is_frozen_and_changes_are_copies() -> None:
    pack = representative_pack()
    with pytest.raises(FrozenInstanceError):
        pack.title = "changed"
    assert pack.with_changes(title="changed").title == "changed"
    assert pack.title != "changed"


def test_unknown_signals_and_blockers_are_preserved() -> None:
    report = seo.score_pack(seo.Pack(), "tiktok")
    assert any(signal.status == seo.Status.UNKNOWN for signal in report.signals)
    assert report.confidence < 1.0
    report = seo.score_pack(
        representative_pack().with_changes(watermark=True), "tiktok"
    )
    assert report.score <= 45
    assert "repost_watermark" in {signal.id for signal in report.blocking}


def test_original_public_import_surface() -> None:
    expected_all = [
        "AbArm",
        "AbEvaluation",
        "AbPlan",
        "CalibrationReport",
        "Engagement",
        "KeywordOpportunity",
        "KeywordReport",
        "METRIC_NAMES",
        "OptimizationPlan",
        "PLATFORM_PROFILES",
        "Pack",
        "PlatformProfile",
        "QuickWin",
        "SeoReport",
        "Signal",
        "calibrate",
        "evaluate_ab_test",
        "keyword_opportunities",
        "optimize_pack",
        "plan_ab_test",
        "platform_rules",
        "score_pack",
        "score_platforms",
    ]
    assert seo.__all__ == expected_all
    owners = {
        "contracts": [
            "DimensionScore",
            "Engagement",
            "Pack",
            "QuickWin",
            "SeoReport",
            "Signal",
            "Status",
        ],
        "profiles": [
            "PLATFORM_PROFILES",
            "PlatformProfile",
            "YOUTUBE",
            "SHORTS",
            "TIKTOK",
        ],
        "experiments": [
            "METRIC_NAMES",
            "AbArm",
            "AbEvaluation",
            "AbPlan",
            "plan_ab_test",
            "evaluate_ab_test",
        ],
        "keywords": [
            "CompetitorVideo",
            "KeywordOpportunity",
            "KeywordReport",
            "keyword_opportunities",
        ],
        "calibration": ["CalibrationReport", "calibrate"],
        "optimization": ["OptimizationPlan", "optimize_pack"],
        "scoring": ["score_pack", "score_platforms", "platform_rules"],
        "_helpers": ["hex_luminance_distance"],
    }
    for owner, names in owners.items():
        module = import_module(f"content_factory.seo.{owner}")
        for name in names:
            assert getattr(seo, name) is getattr(module, name)


def test_seo_modules_remain_under_line_budget() -> None:
    package = Path(seo.__file__).parent
    for path in package.glob("*.py"):
        assert len(path.read_text(encoding="utf-8").splitlines()) < 1100, path.name


def test_legacy_luminance_scale_and_invalid_colors() -> None:
    assert seo.hex_luminance_distance("#000", "#fff") == 1.0
    assert seo.hex_luminance_distance("invalid", "#fff") == 0.0


def test_keyword_freshness_keeps_zero_day_fallback() -> None:
    report = seo.keyword_opportunities(
        ["history"],
        [
            seo.CompetitorVideo("history", days_old=0),
            seo.CompetitorVideo("history", days_old=1),
        ],
    )
    assert report.rows[0].freshness == 0.5
