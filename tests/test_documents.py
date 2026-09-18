"""Tests for federated document search and the lexical reranker."""

from __future__ import annotations

import asyncio

from content_factory.documents import FederatedSearcher, LexicalReranker
from content_factory.models import DocumentResult


def make_result(
    title: str, *, source: str = "arxiv", abstract: str = ""
) -> DocumentResult:
    return DocumentResult(
        id=f"{source}:{title.lower().replace(' ', '-')}",
        title=title,
        authors=["Jane Doe"],
        year=2024,
        abstract=abstract or f"Abstract discussing {title}.",
        source=source,
        pdf_url=f"https://example.org/{title.lower().replace(' ', '-')}.pdf",
        landing_url=f"https://example.org/{title.lower().replace(' ', '-')}",
        is_open_access=True,
    )


# --- Lexical reranker -------------------------------------------------------


def test_reranker_prefers_exact_title_match() -> None:
    exact = make_result("Morning Light and Circadian Rhythms")
    off_topic = make_result("Quantum Computing Advances")
    ranked = LexicalReranker().rerank(
        "morning light circadian rhythms", [off_topic, exact]
    )
    assert ranked[0].title == exact.title
    assert ranked[0].score > ranked[1].score


def test_reranker_penalizes_single_word_match() -> None:
    broad = make_result("Light Bulbs Throughout History")
    precise = make_result("Morning Light Effects on Sleep")
    ranked = LexicalReranker().rerank("morning light sleep", [broad, precise])
    assert ranked[0].title == precise.title


def test_reranker_returns_all_when_query_empty() -> None:
    results = [make_result("Anything")]
    ranked = LexicalReranker().rerank("", results)
    assert ranked == results


# --- Federated searcher -----------------------------------------------------


class FakeProvider:
    def __init__(
        self, name: str, results: list[DocumentResult], *, fail: bool = False
    ) -> None:
        self.name = name
        self._results = results
        self._fail = fail

    async def search(self, query: str, limit: int) -> list[DocumentResult]:
        if self._fail:
            raise RuntimeError("provider down")
        return self._results[:limit]


def test_searcher_merges_and_dedupes() -> None:
    duplicate = make_result("Shared Title", source="arxiv")
    other = make_result("Unique Paper", source="crossref")
    searcher = FederatedSearcher(
        [
            FakeProvider("arxiv", [duplicate]),
            FakeProvider("crossref", [duplicate.model_copy(), other]),
        ]
    )
    results = asyncio.run(searcher.search("shared title"))
    assert len(results) == 2
    assert {r.title for r in results} == {"Shared Title", "Unique Paper"}


def test_searcher_ignores_failing_provider() -> None:
    good = make_result("Working Paper")
    searcher = FederatedSearcher(
        [FakeProvider("broken", [], fail=True), FakeProvider("good", [good])]
    )
    results = asyncio.run(searcher.search("working"))
    assert [r.title for r in results] == ["Working Paper"]


def test_searcher_empty_without_providers() -> None:
    searcher = FederatedSearcher([])
    assert asyncio.run(searcher.search("anything")) == []
    assert searcher.sources == []


def test_searcher_respects_limit() -> None:
    results = [make_result(f"Paper {i}") for i in range(5)]
    searcher = FederatedSearcher([FakeProvider("arxiv", results)])
    assert len(asyncio.run(searcher.search("paper", limit=2))) <= 2


# --- Export helpers ---------------------------------------------------------


def test_result_to_bibtex() -> None:
    result = make_result("Morning Light", abstract="A study.")
    bibtex = result.to_bibtex()
    assert "@article{" in bibtex
    assert "title = {{Morning Light}}" in bibtex
    assert "Jane Doe" in bibtex


def test_result_to_markdown() -> None:
    result = make_result("Morning Light", abstract="A study.")
    markdown = result.to_markdown()
    assert "### [Morning Light]" in markdown
    assert "Jane Doe" in markdown
