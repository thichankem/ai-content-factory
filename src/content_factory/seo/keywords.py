from __future__ import annotations

import math
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from ._helpers import _STOPWORDS, _clamp, _mentions, _words
from .contracts import Pack


@dataclass(frozen=True)
class CompetitorVideo:
    title: str
    views: int = 0
    channel: str = ""
    subscribers: int = 0
    days_old: int | None = None
    duration_seconds: float | None = None


@dataclass(frozen=True)
class KeywordOpportunity:
    keyword: str
    demand: int
    competitors: int
    median_views: float
    median_subscribers: float
    freshness: float
    opportunity: int
    covered: bool
    action: str
    evidence_titles: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "keyword": self.keyword,
            "demand": self.demand,
            "competitors": self.competitors,
            "median_views": round(self.median_views, 1),
            "median_subscribers": round(self.median_subscribers, 1),
            "freshness": round(self.freshness, 3),
            "opportunity": self.opportunity,
            "covered": self.covered,
            "action": self.action,
            "evidence_titles": list(self.evidence_titles),
        }


@dataclass(frozen=True)
class KeywordReport:
    rows: tuple[KeywordOpportunity, ...]
    winning_patterns: tuple[dict[str, Any], ...]
    recommendations: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "rows": [row.to_dict() for row in self.rows],
            "winning_patterns": [dict(pattern) for pattern in self.winning_patterns],
            "recommendations": list(self.recommendations),
        }


def _median(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[middle])
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def keyword_opportunities(
    keywords: Sequence[str],
    competitors: Sequence[CompetitorVideo],
    *,
    pack: Pack | None = None,
) -> KeywordReport:
    rows: list[KeywordOpportunity] = []
    for keyword in keywords:
        keyword = keyword.strip()
        if not keyword:
            continue
        matching = [video for video in competitors if _mentions(video.title, keyword)]
        views = [float(video.views) for video in matching]
        demand = int(sum(views))
        freshness = 0.0
        if matching:
            recent = [video for video in matching if (video.days_old or 999) <= 30]
            freshness = len(recent) / len(matching)
        median_views = _median(views)
        median_subs = _median([float(video.subscribers) for video in matching])
        demand_score = math.log10(demand + 1) / 6.0
        competition_score = math.log10(len(matching) + 1) / 2.0
        authority_penalty = math.log10(median_subs + 1) / 7.0
        opportunity = _clamp(
            0.55 * demand_score
            + 0.20 * freshness
            - 0.20 * competition_score
            - 0.15 * authority_penalty
            + 0.30
        )
        covered = bool(
            pack is not None
            and _mentions(
                " ".join(
                    [
                        pack.title,
                        pack.description,
                        " ".join(pack.tags),
                        " ".join(pack.hashtags),
                    ]
                ),
                keyword,
            )
        )
        if not matching:
            action = "no data — supply competitor rows for this phrase"
        elif covered and opportunity >= 0.6:
            action = "already targeted — defend it in the title"
        elif opportunity >= 0.7:
            action = "target first"
        elif opportunity >= 0.5:
            action = "support with a secondary video"
        else:
            action = "skip — competition outweighs demand"
        rows.append(
            KeywordOpportunity(
                keyword=keyword,
                demand=demand,
                competitors=len(matching),
                median_views=median_views,
                median_subscribers=median_subs,
                freshness=freshness,
                opportunity=int(round(opportunity * 100)),
                covered=covered,
                action=action,
                evidence_titles=tuple(video.title for video in matching[:3]),
            )
        )
    rows.sort(key=lambda row: row.opportunity, reverse=True)
    patterns = _winning_patterns(competitors)
    recommendations: list[str] = []
    if rows:
        top = rows[0]
        recommendations.append(
            f"Lead with {top.keyword!r}: {top.demand:,} views of demand across "
            f"{top.competitors} videos (opportunity {top.opportunity}/100)."
        )
    uncovered = [row for row in rows if not row.covered and row.opportunity >= 60]
    if uncovered:
        recommendations.append(
            "Not covered anywhere in the pack yet: "
            + ", ".join(row.keyword for row in uncovered[:5])
            + "."
        )
    if patterns:
        recommendations.append(
            "Winning title phrasing: "
            + ", ".join(f"{p['pattern']!r}" for p in patterns[:3])
            + "."
        )
    if not competitors:
        recommendations.append(
            "No competitor rows supplied, so every phrase scores as unknown demand; "
            "export 20-50 top results for the niche to get real numbers."
        )
    return KeywordReport(
        rows=tuple(rows),
        winning_patterns=patterns,
        recommendations=tuple(recommendations),
    )


def _winning_patterns(
    competitors: Sequence[CompetitorVideo], *, limit: int = 8
) -> tuple[dict[str, Any], ...]:
    if not competitors:
        return ()
    views = sorted((video.views for video in competitors), reverse=True)
    cutoff = views[len(views) // 4] if len(views) >= 4 else 0.0
    strong = [video for video in competitors if video.views >= cutoff]
    counter: Counter[str] = Counter()
    weight: dict[str, int] = {}
    for video in strong:
        words = [word for word in _words(video.title) if word not in _STOPWORDS]
        for first, second in zip(words, words[1:], strict=False):
            pattern = f"{first} {second}"
            counter[pattern] += 1
            weight[pattern] = weight.get(pattern, 0) + video.views
    patterns = [
        {
            "pattern": pattern,
            "titles": count,
            "views": weight[pattern],
            "views_per_title": int(weight[pattern] / count),
        }
        for pattern, count in counter.most_common(limit * 2)
        if count >= 2
    ]
    patterns.sort(key=lambda row: (row["views_per_title"], row["titles"]), reverse=True)
    return tuple(patterns[:limit])
