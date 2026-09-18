"""Heuristic pre-publish virality scoring over a script.

This is an early-warning signal computed purely from the script text (plus an
optional duration and hook). It needs no platform engagement data, so it can
run offline before anything is published and flag weak areas worth fixing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_CURIOSITY_CUES = (
    "?",
    "why",
    "how",
    "what",
    "when",
    "did",
    "do",
    "you",
    "your",
    "but",
    "never",
    "secret",
    "number",
    "percent",
    "%",
)

_CTA_CUES = (
    "follow",
    "subscribe",
    "share",
    "comment",
    "watch",
    "like",
    "bell",
    "notifications",
)

_SENTENCE_SPLIT = re.compile(r"[.!?\n]+")

_IDEAL_PACE_MIN = 130.0
_IDEAL_PACE_MAX = 170.0
_IDEAL_LENGTH_MIN = 30.0
_IDEAL_LENGTH_MAX = 90.0


@dataclass(frozen=True)
class ViralityScore:
    """Aggregate virality heuristic for one script."""

    score: int  # 0-100
    breakdown: dict[str, float]
    warnings: list[str]


def score_hook(hook: str) -> float:
    """Rate hook quality from 0..1 based on brevity and curiosity cues."""
    words = hook.split()
    if not words:
        return 0.0
    short = len(words) < 12
    lowered = hook.lower()
    cues = sum(1 for cue in _CURIOSITY_CUES if cue in lowered)
    if re.search(r"\d", hook) is not None:
        cues += 1
    score = (0.6 if short else 0.0) + min(0.4, cues * 0.08)
    if not short:
        score -= 0.1
    return round(float(max(0.0, min(1.0, score))), 3)


def _first_sentence(text: str) -> str:
    parts = [part.strip() for part in _SENTENCE_SPLIT.split(text) if part.strip()]
    return parts[0] if parts else text


def _has_cta(text: str) -> bool:
    lowered = text.lower()
    return any(cue in lowered for cue in _CTA_CUES)


def score_virality(
    script: str,
    *,
    duration_seconds: float | None = None,
    hook: str | None = None,
) -> ViralityScore:
    """Score a script's viral potential from 0..100 and collect warnings.

    Four weighted components are summed: hook strength (0-30), pace (0-30),
    length fit (0-20) and call-to-action (0-20). ``duration_seconds`` is
    optional; when absent the pace and length components fall back to neutral
    values.
    """
    text = script.strip()
    if not text:
        return ViralityScore(
            0, {"hook": 0.0, "pace": 0.0, "length": 0.0, "cta": 0.0}, ["empty script"]
        )

    word_count = len(text.split())

    # Hook strength (0-30): reuse the standalone hook scorer on the opening.
    active_hook = hook if hook is not None else _first_sentence(text)
    hook_score = score_hook(active_hook) * 30.0

    # Pace (0-30): words-per-minute, ideal 130-170.
    wpm: float | None = None
    if duration_seconds is not None and duration_seconds > 0:
        wpm = word_count / (duration_seconds / 60.0)
    if wpm is None:
        pace_score = 20.0
    elif _IDEAL_PACE_MIN <= wpm <= _IDEAL_PACE_MAX:
        pace_score = 30.0
    elif 100.0 <= wpm < _IDEAL_PACE_MIN or _IDEAL_PACE_MAX < wpm <= 200.0:
        pace_score = 22.0
    else:
        pace_score = 12.0

    # Length fit (0-20): shorts sit best in the 30-90s band.
    if duration_seconds is None:
        length_score = 15.0
    elif _IDEAL_LENGTH_MIN <= duration_seconds <= _IDEAL_LENGTH_MAX:
        length_score = 20.0
    elif duration_seconds <= 240.0:
        length_score = 15.0
    else:
        length_score = 8.0

    # Call to action (0-20).
    cta_score = 20.0 if _has_cta(text) else 0.0

    total = int(
        round(max(0.0, min(100.0, hook_score + pace_score + length_score + cta_score)))
    )

    warnings: list[str] = []
    if hook_score < 18.0:
        warnings.append("hook too long or lacks curiosity")
    if cta_score == 0.0:
        warnings.append("no CTA")
    if wpm is not None and wpm < 100.0:
        warnings.append("too slow pace")
    elif wpm is not None and wpm > 200.0:
        warnings.append("too fast pace")
    if duration_seconds is not None and duration_seconds > 360.0:
        warnings.append("video likely too long for shorts")

    breakdown = {
        "hook": round(hook_score, 2),
        "pace": round(pace_score, 2),
        "length": round(length_score, 2),
        "cta": round(cta_score, 2),
    }
    return ViralityScore(total, breakdown, warnings)
