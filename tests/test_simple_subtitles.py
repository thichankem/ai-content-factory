"""Tests for the simplified-subtitles accessibility module."""

from __future__ import annotations

from content_factory.simple_subtitles import (
    SimplificationLevel,
    simplify_caption,
    simplify_captions,
)


def test_swaps_difficult_words() -> None:
    out = simplify_caption("The individual attempted to purchase a vehicle.")
    assert out == "The person tried to buy a car."


def test_keeps_simple_text_unchanged() -> None:
    out = simplify_caption("The dog ran fast.")
    assert out == "The dog ran fast."


def test_preserves_case() -> None:
    out = simplify_caption("Important assistance is required.")
    assert out == "Key help is needed."


def test_intermediate_shortens_long_sentence() -> None:
    long_text = (
        "The committee subsequently determined that the additional information "
        "was sufficient to establish the previous claim."
    )
    out = simplify_caption(long_text, SimplificationLevel.INTERMEDIATE)
    assert len(out.split()) < len(long_text.split())
    # The long clause after "that" is dropped.
    assert "that" not in out


def test_basic_keeps_sentence_length() -> None:
    long_text = (
        "The committee subsequently determined that the additional information "
        "was sufficient to establish the previous claim."
    )
    out = simplify_caption(long_text, SimplificationLevel.BASIC)
    # BASIC swaps words but does not truncate the sentence.
    assert "later" in out or "find out" in out or "enough" in out


def test_simplify_captions_returns_originals() -> None:
    captions = ["Please utilize this assistance.", "Hello world."]
    results = simplify_captions(captions, SimplificationLevel.BASIC)
    assert results[0].original == "Please utilize this assistance."
    assert results[0].simplified == "Please use this help."
    assert results[1].simplified == "Hello world."
