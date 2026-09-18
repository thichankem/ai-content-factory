from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Any


class Status(StrEnum):
    OK = "ok"
    WARN = "warn"
    FAIL = "fail"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Engagement:
    impressions: int = 0
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    follows: int = 0
    watch_time_seconds: float = 0.0
    average_view_seconds: float | None = None
    completion_rate: float | None = None

    def ctr_pct(self) -> float | None:
        if self.impressions <= 0:
            return None
        return self.views / self.impressions * 100.0

    def avd_ratio(self, duration: float | None) -> float | None:
        if self.average_view_seconds is not None and duration:
            return self.average_view_seconds / duration
        if self.watch_time_seconds > 0 and self.views > 0 and duration:
            return (self.watch_time_seconds / self.views) / duration
        return None


@dataclass(frozen=True)
class Pack:
    title: str = ""
    description: str = ""
    tags: tuple[str, ...] = ()
    hashtags: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()
    script: str = ""
    hook: str = ""
    duration_seconds: float | None = None
    aspect_ratio: str = ""
    thumbnail_present: bool | None = None
    thumbnail_text: str = ""
    on_screen_text: tuple[str, ...] = ()
    has_captions: bool | None = None
    caption_source: str = ""
    has_chapters: bool = False
    chapter_count: int = 0
    has_end_screen: bool | None = None
    playlist: str | None = None
    sound: str = ""
    sound_trending: bool | None = None
    beat_synced: bool | None = None
    bpm: int | None = None
    cuts_per_minute: float | None = None
    loop_friendly: bool | None = None
    intro_seconds: float | None = None
    text_in_safe_zone: bool | None = None
    publish_hour: int | None = None
    audience_hours: tuple[int, ...] = ()
    watermark: bool | None = None
    comment_prompt: bool = False
    series_part: int | None = None
    duet_stitch_enabled: bool | None = None
    channel: str = ""
    language: str = "vi"
    engagement: Engagement | None = None

    @property
    def primary_keyword(self) -> str:
        return self.keywords[0] if self.keywords else ""

    def with_changes(self, **changes: Any) -> Pack:
        return replace(self, **changes)


@dataclass(frozen=True)
class Signal:
    id: str
    label: str
    dimension: str
    weight: float
    score: float | None
    status: Status
    detail: str
    fix: str | None = None
    blocking: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "dimension": self.dimension,
            "weight": self.weight,
            "score": None if self.score is None else round(self.score, 3),
            "status": str(self.status),
            "detail": self.detail,
            "fix": self.fix,
            "blocking": self.blocking,
        }


@dataclass(frozen=True)
class QuickWin:
    signal_id: str
    label: str
    points: float
    fix: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "label": self.label,
            "points": round(self.points, 1),
            "fix": self.fix,
        }


@dataclass(frozen=True)
class DimensionScore:
    key: str
    label: str
    weight: float
    score: float
    coverage: float
    signals: tuple[Signal, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "weight": self.weight,
            "score": round(self.score, 1),
            "coverage": round(self.coverage, 3),
            "signals": [signal.to_dict() for signal in self.signals],
        }


@dataclass(frozen=True)
class SeoReport:
    platform: str
    label: str
    score: int
    grade: str
    confidence: float
    capped: bool
    cap_reason: str | None
    dimensions: tuple[DimensionScore, ...]
    blocking: tuple[Signal, ...]
    quick_wins: tuple[QuickWin, ...]
    projected_score: int
    verdict: str
    metrics: dict[str, float]
    notes: tuple[str, ...]

    @property
    def signals(self) -> tuple[Signal, ...]:
        return tuple(
            signal for dimension in self.dimensions for signal in dimension.signals
        )

    @property
    def precision(self) -> float:
        """Un-rounded weighted score.

        ``score`` is an integer for humans; this is the same number before
        rounding, so callers comparing two close packs (the optimiser does)
        can tell a real 0.4-point improvement from a tie.
        """
        return sum(dimension.weight * dimension.score for dimension in self.dimensions)

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "label": self.label,
            "score": self.score,
            "grade": self.grade,
            "confidence": round(self.confidence, 3),
            "capped": self.capped,
            "cap_reason": self.cap_reason,
            "projected_score": self.projected_score,
            "verdict": self.verdict,
            "dimensions": [dimension.to_dict() for dimension in self.dimensions],
            "blocking": [signal.to_dict() for signal in self.blocking],
            "quick_wins": [win.to_dict() for win in self.quick_wins],
            "metrics": {key: round(value, 4) for key, value in self.metrics.items()},
            "notes": list(self.notes),
        }
