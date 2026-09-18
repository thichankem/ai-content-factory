"""Tests for the compliance critic, audit trail, and cost guard."""

from __future__ import annotations

import pytest

from content_factory.audit import AuditLog
from content_factory.compliance import (
    BrandKit,
    BrandMeta,
    ComplianceMeta,
    check_brand,
    check_copyright,
    check_platform,
    fingerprint_music_audio,
)
from content_factory.cost_guard import (
    CostEstimate,
    CostGuard,
    PlanBudget,
    estimate_cost,
    should_confirm,
)
from content_factory.models import IssueSeverity

# --- check_platform -----------------------------------------------------------


def test_platform_flags_too_long_tiktok() -> None:
    meta = ComplianceMeta(duration_seconds=601.0, aspect_ratio="9:16", words=100)
    issues = check_platform(meta, "tiktok")
    assert any(
        issue.code == "duration_too_long" and issue.severity == IssueSeverity.ERROR
        for issue in issues
    )


def test_platform_passes_compliant_youtube() -> None:
    meta = ComplianceMeta(
        duration_seconds=300.0, aspect_ratio="16:9", words=100, text="hello world"
    )
    assert check_platform(meta, "youtube") == []


def test_platform_flags_forbidden_pattern() -> None:
    meta = ComplianceMeta(
        duration_seconds=60.0,
        aspect_ratio="9:16",
        words=50,
        text="Please subscribe now to my channel!",
    )
    issues = check_platform(meta, "tiktok")
    assert any(
        issue.code == "forbidden_pattern" and issue.severity == IssueSeverity.WARNING
        for issue in issues
    )


def test_platform_unknown_returns_empty() -> None:
    meta = ComplianceMeta(duration_seconds=9999.0, aspect_ratio="4:3")
    assert check_platform(meta, "not_a_platform") == []


# --- check_brand --------------------------------------------------------------


def test_brand_flags_missing_logo_and_off_palette() -> None:
    kit = BrandKit(palette=("#ff0000",), fonts=("Inter",), logo_fingerprints=())
    meta = BrandMeta(
        dominant_colors=("#00ff00",), fonts_used=("Inter",), has_logo=False
    )
    issues = check_brand(meta, kit)
    assert any(
        issue.code == "missing_logo" and issue.severity == IssueSeverity.ERROR
        for issue in issues
    )
    assert any(
        issue.code == "off_palette" and issue.severity == IssueSeverity.WARNING
        for issue in issues
    )


def test_brand_passes_when_everything_matches() -> None:
    kit = BrandKit(palette=("#ff0000",), fonts=("Inter",), logo_fingerprints=())
    meta = BrandMeta(dominant_colors=("#ff0000",), fonts_used=("Inter",), has_logo=True)
    assert check_brand(meta, kit) == []


# --- check_copyright ----------------------------------------------------------


def test_copyright_flags_exact_match() -> None:
    issues = check_copyright("fp-abc", ("fp-abc", "fp-def"))
    assert any(
        issue.code == "copyright_match" and issue.severity == IssueSeverity.ERROR
        for issue in issues
    )


def test_copyright_passes_without_match() -> None:
    assert check_copyright("fp-xyz", ("fp-abc", "fp-def")) == []


# --- fingerprint_music_audio --------------------------------------------------


def test_fingerprint_music_audio_missing_file_raises(tmp_path) -> None:
    with pytest.raises(ValueError):
        fingerprint_music_audio(str(tmp_path / "missing.wav"))


# --- AuditLog -----------------------------------------------------------------


def test_audit_roundtrip_and_newest_first(tmp_path) -> None:
    log = AuditLog(str(tmp_path))
    log.record("alice", "create", project_id="p1")
    log.record("bob", "approve", project_id="p1", media_id="m1")
    log.record("carol", "publish", project_id="p1")

    entries = log.entries()
    assert [entry.action for entry in entries] == ["publish", "approve", "create"]
    assert entries[0].actor == "carol"
    assert entries[0].project_id == "p1"
    assert entries[1].media_id == "m1"
    assert log.count() == 3


def test_audit_skips_corrupt_line(tmp_path) -> None:
    log = AuditLog(str(tmp_path))
    log.record("alice", "create")
    with (tmp_path / "audit.jsonl").open("a", encoding="utf-8") as handle:
        handle.write("{not valid json}\n")

    entries = log.entries()
    assert len(entries) == 1
    assert entries[0].actor == "alice"
    assert log.count() == 1


# --- cost_guard ---------------------------------------------------------------


def test_estimate_cost_computes_totals() -> None:
    estimate = estimate_cost({"vision": 3, "tts": 2})
    assert estimate.total_usd == pytest.approx(0.034)
    assert estimate.breakdown["vision"] == pytest.approx(0.03)
    assert estimate.breakdown["tts"] == pytest.approx(0.004)
    assert estimate.calls == {"vision": 3, "tts": 2}


def test_estimate_cost_unknown_keys_are_zero() -> None:
    estimate = estimate_cost({"unknown_step": 5})
    assert estimate.total_usd == 0.0


def test_should_confirm_boundary() -> None:
    at_threshold = CostEstimate(total_usd=1.0, breakdown={}, calls={})
    assert should_confirm(at_threshold, 1.0) is False
    above = CostEstimate(total_usd=1.01, breakdown={}, calls={})
    assert should_confirm(above, 1.0) is True


def test_cost_guard_disabled_never_confirms() -> None:
    budget = PlanBudget(
        enabled=False, threshold_usd=0.001, unit_costs={"vision": 0.010}
    )
    guard = CostGuard(budget)
    estimate, needs_confirmation = guard.check({"vision": 100})
    assert needs_confirmation is False
    assert estimate.total_usd == pytest.approx(1.0)
