"""Tests for the sound-effect synthesis module."""

from __future__ import annotations

import numpy as np
import pytest

from content_factory.sfx import SfxError, sfx_catalog, synthesize_sfx


def test_all_sfx_registered() -> None:
    for name in (
        "whoosh",
        "impact",
        "explosion",
        "footstep",
        "ambience",
        "transition",
        "ui_click",
    ):
        assert name in synthesize_sfx.__globals__["SFX"]


def test_unknown_sfx_raises() -> None:
    with pytest.raises(SfxError, match="Unknown SFX"):
        synthesize_sfx("nope")


def test_each_sfx_produces_pcm() -> None:
    sr = 44100
    for name in synthesize_sfx.__globals__["SFX"]:
        out = synthesize_sfx(name, sr, {"duration": 0.5, "seed": 1})
        assert out.dtype == np.float32
        assert out.ndim == 1
        assert len(out) > 0
        assert np.all(np.isfinite(out))


def test_sfx_catalog_has_descriptions() -> None:
    cat = sfx_catalog()
    names = {s["name"] for s in cat["sfx"]}
    assert "whoosh" in names
    for entry in cat["sfx"]:
        assert entry["description"]


def test_impact_is_short_and_decaying() -> None:
    out = synthesize_sfx("impact", 44100, {"duration": 0.25})
    assert len(out) < 44100
    # Decays: tail quieter than the onset.
    assert float(np.max(np.abs(out[:1000]))) > float(np.max(np.abs(out[-1000:])))
