"""Semantic-search seam over the media library (transcripts + filenames).

A small, dependency-light index that ranks media items by how well they match a
query. Ranking is lexical by default (a simple TF-IDF/BM25-style score); when an
:class:`Embedder` is wired in, the lexical score is fused with cosine similarity
of dense embeddings. The embedder is only a seam — no model is required, so the
whole module runs offline and is trivially testable.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol

from .text import tokenize

# A small built-in English stopword set used by :func:`_tokenize`.
_STOPWORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "but",
        "if",
        "then",
        "else",
        "for",
        "to",
        "of",
        "in",
        "on",
        "at",
        "by",
        "with",
        "from",
        "as",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "can",
        "could",
        "should",
        "may",
        "might",
        "must",
        "shall",
        "not",
        "so",
        "too",
        "very",
        "it",
        "this",
        "that",
        "these",
        "those",
        "i",
        "you",
        "he",
        "she",
        "we",
        "they",
        "them",
        "his",
        "her",
        "its",
        "their",
        "what",
        "which",
        "who",
        "whom",
        "when",
        "where",
        "why",
        "how",
        "all",
        "any",
        "both",
        "each",
        "more",
        "most",
        "some",
        "such",
        "no",
        "nor",
        "only",
        "own",
        "same",
        "than",
        "up",
        "down",
        "into",
        "over",
        "under",
        "again",
        "further",
        "once",
        "here",
        "there",
        "about",
        "above",
        "below",
        "between",
        "during",
        "through",
        "before",
        "after",
        "while",
        "because",
        "until",
        "against",
        "among",
        "upon",
        "around",
        "along",
        "within",
        "without",
    }
)


class Embedder(Protocol):
    """Embeds a piece of text into a dense vector.

    Implementations may wrap a local model or a remote API; the search index
    only relies on this one method.
    """

    def embed(self, text: str) -> list[float]: ...


@dataclass(frozen=True)
class SearchHit:
    """One ranked match against the media library."""

    media_id: str
    filename: str
    kind: str
    score: float
    snippet: str


@dataclass
class _IndexEntry:
    """Internal record for one indexed media item."""

    media_id: str
    filename: str
    kind: str
    text: str
    tokens: list[str]
    embedding: list[float] | None = None


def _tokenize(text: str) -> list[str]:
    """Lowercase, split on non-alphanumerics, and drop stopwords."""
    return tokenize(text, stopwords=_STOPWORDS)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors; 0.0 for empty or zero-norm input."""
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class MediaSearchIndex:
    """An in-memory search index over media transcripts and filenames."""

    def __init__(self, embedder: Embedder | None = None) -> None:
        self._embedder = embedder
        self._entries: list[_IndexEntry] = []

    def add(self, media_id: str, filename: str, kind: str, text: str) -> None:
        """Store one media item for later search."""
        tokens = _tokenize(f"{filename} {text}")
        embedding = self._embedder.embed(text) if self._embedder is not None else None
        self._entries.append(
            _IndexEntry(
                media_id=media_id,
                filename=filename,
                kind=kind,
                text=text,
                tokens=tokens,
                embedding=embedding,
            )
        )

    def size(self) -> int:
        """Number of indexed items."""
        return len(self._entries)

    def clear(self) -> None:
        """Remove every indexed item."""
        self._entries.clear()

    def search(self, query: str, *, top_k: int = 10) -> list[SearchHit]:
        """Return the ``top_k`` items most relevant to ``query``.

        A lexical TF-IDF score is always computed. When an embedder is wired
        in, the final score fuses cosine similarity with the normalized lexical
        score: ``0.6 * cosine + 0.4 * normalized_lexical``. Hits are sorted
        descending by final score, each with a leading snippet of its text.
        """
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        lexical_scores = [
            self._lexical_score(query_tokens, entry) for entry in self._entries
        ]
        max_lexical = max(lexical_scores) if lexical_scores else 0.0
        query_embedding: list[float] | None = (
            self._embedder.embed(query) if self._embedder is not None else None
        )

        scored: list[tuple[float, _IndexEntry]] = []
        for entry, lexical in zip(self._entries, lexical_scores, strict=False):
            normalized = lexical / max_lexical if max_lexical > 0 else 0.0
            if (
                self._embedder is not None
                and entry.embedding is not None
                and query_embedding is not None
            ):
                cosine = cosine_similarity(query_embedding, entry.embedding)
                final = 0.6 * cosine + 0.4 * normalized
            else:
                final = normalized
            scored.append((final, entry))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        hits: list[SearchHit] = []
        for score, entry in scored[: max(0, top_k)]:
            hits.append(
                SearchHit(
                    media_id=entry.media_id,
                    filename=entry.filename,
                    kind=entry.kind,
                    score=round(float(score), 4),
                    snippet=entry.text[:160],
                )
            )
        return hits

    def _lexical_score(self, query_tokens: list[str], entry: _IndexEntry) -> float:
        """Simple TF-IDF score of ``entry`` against the query terms."""
        doc_len = len(entry.tokens)
        if doc_len == 0:
            return 0.0
        total_docs = self.size()
        score = 0.0
        for term in set(query_tokens):
            term_frequency = entry.tokens.count(term) / doc_len
            doc_frequency = sum(1 for other in self._entries if term in other.tokens)
            inverse_doc_frequency = (
                math.log((total_docs + 1) / (doc_frequency + 1)) + 1.0
            )
            score += term_frequency * inverse_doc_frequency
        return score
