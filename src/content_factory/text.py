"""Shared text helpers: title keys, slugs and the project's tokenizers.

Four modules used to carry their own near-identical tokenizer, each with a
slightly different rule. They now share the single implementation here and
pass their policy in, so a ranking change is made in exactly one place.
"""

from __future__ import annotations

import re
from collections.abc import Collection

#: ASCII word characters, used by the lexical/BM25 tokenizers.
_ALNUM_RE = re.compile(r"[a-z0-9]+")

#: Unicode-aware word characters, so languages with diacritics (Vietnamese,
#: for example) keep their whole words instead of being split on them.
_WORD_RE = re.compile(r"\w+", re.UNICODE)


def normalize_title(title: str) -> str:
    """Reduce a title to a comparison key (lowercase alphanumerics only)."""
    return re.sub(r"[^a-z0-9]+", "", (title or "").lower())


def slugify(title: str, max_length: int = 48) -> str:
    """Turn a title into a short, URL-safe slug."""
    return re.sub(r"[^a-z0-9]+", "-", (title or "").lower()).strip("-")[:max_length]


def tokenize(
    text: str,
    *,
    min_length: int = 1,
    stopwords: Collection[str] = (),
) -> list[str]:
    """Lowercase alphanumeric tokens, optionally filtered by length/stopwords."""
    return [
        word
        for word in _ALNUM_RE.findall((text or "").lower())
        if len(word) >= min_length and word not in stopwords
    ]


def word_tokens(text: str) -> list[str]:
    """Unicode-aware tokens, for BM25, embeddings and n-gram scoring."""
    return [word.lower() for word in _WORD_RE.findall(text or "")]
