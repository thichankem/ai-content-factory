"""Tests for the video accessibility layer (catalog, describe, timeline, suggest)."""

from __future__ import annotations

import pytest

from content_factory import video_assist
from content_factory.models import VideoProject, VideoScene


def _project() -> VideoProject:
    return VideoProject(
        scenes=[
            VideoScene(
                id="s1", label="Intro", text="Hello world", duration_seconds=3.0
            ),
            VideoScene(
                id="s2", label="Body", text="More words here", duration_seconds=2.0
            ),
        ],
        aspect_ratio="9:16",
        fps=30,
        captions=True,
    )


def test_catalog_grouped_by_category() -> None:
    cat = video_assist.catalog()
    assert "categories" in cat
    names = {op["name"] for group in cat["ops"].values() for op in group}
    assert {
        "split_scene",
        "audio_mix",
        "render_video",
        "video_effect_glitch",
        "audio_effect_reverb",
    } <= names


def test_describe_operation_known_and_unknown() -> None:
    info = video_assist.describe_operation("split_scene")
    assert info["name"] == "split_scene"
    assert "scene" in info["description"].lower()
    with pytest.raises(ValueError):
        video_assist.describe_operation("nope")


def test_describe_timeline() -> None:
    desc = video_assist.describe_timeline(_project())
    assert desc["summary"]
    assert desc["details"]["scene_count"] == 2
    assert desc["details"]["aspect_ratio"] == "9:16"


def test_suggest_edits_returns_steps() -> None:
    sugg = video_assist.suggest_edits(_project())
    assert "suggestions" in sugg
    assert "summary" in sugg
    for s in sugg["suggestions"]:
        assert s["op"]
        assert s["reason"]


def test_suggest_edits_flat_look() -> None:
    sugg = video_assist.suggest_edits(_project())
    ops = {s["op"] for s in sugg["suggestions"]}
    assert "ai_assist" in ops  # flat look triggers an ai_assist suggestion


def test_effect_docs_folded_in() -> None:
    cat = video_assist.catalog()
    all_names = {op["name"] for group in cat["ops"].values() for op in group}
    assert "video_effect_film_grain" in all_names
    assert "audio_effect_compressor" in all_names
