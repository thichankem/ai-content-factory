"""Tests for the research engine."""

from __future__ import annotations

from content_factory.research import ResearchEngine


def test_research_returns_sources_and_facts() -> None:
    bundle = ResearchEngine().research("morning light and attention")
    assert len(bundle.sources) >= 2
    assert bundle.key_facts
    assert bundle.notes is not None
    assert bundle.generated_at is not None


def test_research_always_includes_field_note() -> None:
    bundle = ResearchEngine().research("quantum basket weaving")
    titles = [s.title for s in bundle.sources]
    assert any(title.startswith("Field note:") for title in titles)


def test_research_matches_relevant_sources() -> None:
    bundle = ResearchEngine().research("morning light circadian sleep")
    titles = [s.title for s in bundle.sources]
    assert any("Circadian" in title for title in titles)


def test_research_respects_max_sources() -> None:
    bundle = ResearchEngine(max_sources=3).research("habits and attention")
    assert len(bundle.sources) <= 3


def test_research_sources_have_highlights_and_relevance() -> None:
    bundle = ResearchEngine().research("storytelling hooks")
    for source in bundle.sources:
        assert source.id
        assert source.url
        assert source.source_type
        assert source.summary
        assert 0.0 <= source.relevance <= 1.0
    assert any(len(s.highlights) > 0 for s in bundle.sources)


def test_research_key_facts_are_grounded_in_sources() -> None:
    bundle = ResearchEngine().research("attention")
    for fact in bundle.key_facts:
        assert ": " in fact  # prefixed by source title
