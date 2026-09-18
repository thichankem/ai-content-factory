"""Tests for the photo accessibility layer: histogram, image description,
per-op plain-language docs, and histogram-based auto-suggestions."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from content_factory import photo_assist
from content_factory.image_engine import ImageError


def _make(size=(100, 100), color=(120, 120, 120, 255)) -> Image.Image:
    return Image.new("RGBA", size, color)


def _png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def test_catalog_grouped_by_category() -> None:
    cat = photo_assist.catalog()
    assert "categories" in cat
    assert "ops" in cat
    assert "light" in cat["categories"]
    assert "retouch" in cat["categories"]
    # A core op and an extended op both appear with docs.
    names = {op["name"] for group in cat["ops"].values() for op in group}
    assert {"exposure", "crop", "white_balance", "liquify"} <= names


def test_describe_op_known_and_unknown() -> None:
    info = photo_assist.describe_op("exposure")
    assert info["name"] == "exposure"
    assert "stops" in info["description"].lower()
    assert "ev" in info["params"]
    with pytest.raises(ImageError):
        photo_assist.describe_op("does_not_exist")


def test_histogram_shape() -> None:
    h = photo_assist.histogram(_make())
    assert h["width"] == 100
    assert h["height"] == 100
    assert "luminance" in h
    assert set(h["channels"]) == {"red", "green", "blue"}
    assert len(h["channels"]["red"]["histogram"]) == 256


def test_describe_image_returns_summary_and_details() -> None:
    desc = photo_assist.describe_image(_make(color=(30, 30, 30, 255)))  # dark
    assert desc["summary"]
    assert desc["details"]["brightness"] == "very dark / underexposed"
    assert "histogram" in desc


def test_describe_image_neutral() -> None:
    desc = photo_assist.describe_image(_make(color=(128, 128, 128, 255)))
    assert "neutral" in desc["details"]["colour_cast"]


def test_suggest_edits_underexposed_suggests_exposure() -> None:
    sugg = photo_assist.suggest_edits(_make(color=(20, 20, 20, 255)))
    ops = {s["op"] for s in sugg["suggestions"]}
    assert "exposure" in ops


def test_suggest_edits_warm_cast_suggests_white_balance() -> None:
    sugg = photo_assist.suggest_edits(_make(color=(220, 150, 120, 255)))
    ops = {s["op"] for s in sugg["suggestions"]}
    assert "white_balance" in ops


def test_suggest_edits_returns_reason_for_each() -> None:
    sugg = photo_assist.suggest_edits(_make(color=(20, 20, 20, 255)))
    for s in sugg["suggestions"]:
        assert s["reason"]
        assert "params" in s


def test_catalog_presets_included() -> None:
    cat = photo_assist.catalog()
    assert "thumbnail" in cat["presets"]
