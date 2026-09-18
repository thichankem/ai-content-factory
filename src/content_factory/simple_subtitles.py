"""Accessibility: simplified subtitles for kids and language learners.

Takes a normal subtitle/caption line and produces an easier-to-read version:
long or uncommon words are swapped for simpler synonyms, overly long sentences
are shortened, and filler is dropped. Deterministic and offline — no model.

The goal is *readability*, not translation: the simplified line keeps the same
meaning but uses simpler vocabulary and shorter phrasing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class SimplificationLevel(StrEnum):
    """How aggressively to simplify."""

    BASIC = "basic"  # swap difficult words, keep sentence structure
    INTERMEDIATE = "intermediate"  # also shorten long sentences and drop filler


# Common difficult -> simpler synonym map (lowercased source).
_SYNONYMS: dict[str, str] = {
    "approximately": "about",
    "attempt": "try",
    "assistance": "help",
    "commence": "start",
    "consequently": "so",
    "demonstrate": "show",
    "difficult": "hard",
    "enormous": "huge",
    "frequently": "often",
    "immediately": "now",
    "important": "key",
    "individual": "person",
    "numerous": "many",
    "obtain": "get",
    "occurred": "happened",
    "purchase": "buy",
    "remain": "stay",
    "require": "need",
    "required": "needed",
    "sufficient": "enough",
    "terminate": "end",
    "utilize": "use",
    "vehicle": "car",
    "additional": "more",
    "advantage": "benefit",
    "alternative": "choice",
    "assemble": "gather",
    "attempted": "tried",
    "communicate": "talk",
    "construct": "build",
    "determine": "find out",
    "establish": "set up",
    "investigate": "look into",
    "participate": "join",
    "possess": "have",
    "previous": "earlier",
    "subsequent": "later",
    "therefore": "so",
    "transparent": "clear",
    "unusual": "odd",
    "voluntary": "optional",
}

_FILLER = re.compile(
    r"\b(actually|basically|literally|really|quite|just|very|kind of|sort of)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class SimplifiedCaption:
    """A caption line plus its simplified form."""

    original: str
    simplified: str
    level: SimplificationLevel


def _swap_words(text: str) -> str:
    """Replace difficult words with simpler synonyms (case-preserving)."""

    def replace(match: re.Match[str]) -> str:
        word = match.group(0)
        replacement = _SYNONYMS.get(word.lower())
        if replacement is None:
            return word
        if word.isupper():
            return replacement.upper()
        if word[:1].isupper():
            return replacement.capitalize()
        return replacement

    return re.sub(r"[A-Za-z']+", replace, text)


def _shorten(text: str) -> str:
    """Drop filler and, if still long, keep only the first clause."""
    text = _FILLER.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text.split()) <= 12:
        return text
    # Keep the first sentence/clause; drop the rest.
    first = re.split(r"(?<=[.!?])\s+|,\s+|\b(and|but|so|because|which|that)\b", text)[0]
    return (first or text).strip().rstrip(",")


def simplify_caption(
    text: str, level: SimplificationLevel = SimplificationLevel.BASIC
) -> str:
    """Return a simplified version of one caption line."""
    swapped = _swap_words(text or "")
    if level == SimplificationLevel.INTERMEDIATE:
        swapped = _shorten(swapped)
    return swapped.strip()


def simplify_captions(
    captions: list[str], level: SimplificationLevel = SimplificationLevel.BASIC
) -> list[SimplifiedCaption]:
    """Simplify a list of caption lines, keeping originals for comparison."""
    return [
        SimplifiedCaption(
            original=line,
            simplified=simplify_caption(line, level),
            level=level,
        )
        for line in captions
    ]
