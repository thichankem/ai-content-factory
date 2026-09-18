from __future__ import annotations

import re
import unicodedata

from ..text import tokenize

_PLACEBO_HASHTAGS = frozenset(
    {"fyp", "foryou", "foryoupage", "viral", "trending", "fypシ", "fy"}
)
_STOPWORDS = frozenset(
    {
        "the",
        "and",
        "for",
        "you",
        "your",
        "with",
        "that",
        "this",
        "from",
        "what",
        "when",
        "why",
        "how",
        "are",
        "was",
        "were",
        "will",
        "can",
        "all",
        "not",
        "but",
        "his",
        "her",
        "its",
        "our",
        "they",
        "them",
        "cua",
        "voi",
        "cho",
        "nhu",
        "nay",
        "do",
        "la",
        "va",
        "co",
        "mot",
        "nhung",
        "khi",
        "tai",
        "sao",
        "gi",
    }
)


def _fold(text: str) -> str:
    lowered = unicodedata.normalize("NFD", (text or "").lower())
    stripped = "".join(ch for ch in lowered if not unicodedata.combining(ch))
    return stripped.replace("đ", "d").replace("\u0301", "")


def _words(text: str) -> list[str]:
    return tokenize(_fold(text))


def _mentions(text: str, phrase: str) -> int:
    needle = _fold(phrase).strip()
    if not needle:
        return 0
    haystack = _fold(text)
    count = 0
    start = 0
    while True:
        index = haystack.find(needle, start)
        if index < 0:
            return count
        before = haystack[index - 1] if index else " "
        after_index = index + len(needle)
        after = haystack[after_index] if after_index < len(haystack) else " "
        if not before.isalnum() and not after.isalnum():
            count += 1
        start = index + max(1, len(needle))
    return count


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _band(
    value: float | None,
    low: float,
    high: float,
    *,
    falloff: float | None = None,
) -> float | None:
    if value is None:
        return None
    if low <= value <= high:
        return 1.0
    span = falloff if falloff is not None else max(low * 0.8, (high - low), 1.0)
    gap = (low - value) if value < low else (value - high)
    return _clamp(1.0 - gap / span)


def _ratio(actual: float | None, target: float) -> float | None:
    if actual is None:
        return None
    if target <= 0:
        return 1.0
    return _clamp(actual / target)


def _front_load(text: str, phrase: str, zone: int) -> float | None:
    needle = _fold(phrase).strip()
    if not needle:
        return None
    index = _fold(text).find(needle)
    if index < 0:
        return 0.0
    if index <= zone:
        return 1.0
    return max(0.35, 1.0 - (index - zone) / max(1.0, float(zone)))


_SENTENCE_RE = re.compile(r"[.!?\n]+")


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in _SENTENCE_RE.split(text) if part.strip()]


def hex_luminance_distance(a: str, b: str) -> float:
    try:
        luma = [_luma(color) for color in (a, b)]
    except ValueError:
        return 0.0
    return abs(luma[0] - luma[1])


def _luma(color: str) -> float:
    value = color.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    if len(value) != 6:
        raise ValueError(f"not a hex colour: {color!r}")
    red = int(value[0:2], 16) / 255
    green = int(value[2:4], 16) / 255
    blue = int(value[4:6], 16) / 255
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue
