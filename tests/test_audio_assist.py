"""Tests for the audio accessibility layer (catalog, describe, mastering)."""

from __future__ import annotations

import numpy as np
import pytest

from content_factory import audio_assist


def _sine(freq=440, seconds=1.0, amp=0.5) -> np.ndarray:
    t = np.arange(int(44100 * seconds), dtype=np.float32) / 44100
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def test_catalog_grouped_by_category() -> None:
    cat = audio_assist.catalog()
    assert "categories" in cat
    names = {op["name"] for group in cat["ops"].values() for op in group}
    assert {"audio_mix", "effect_reverb", "sfx_whoosh", "analyze_audio"} <= names


def test_describe_operation_known_and_unknown() -> None:
    info = audio_assist.describe_operation("audio_mix")
    assert info["name"] == "audio_mix"
    assert "mix" in info["description"].lower()
    with pytest.raises(ValueError):
        audio_assist.describe_operation("nope")


def test_describe_effect_and_sfx() -> None:
    eff = audio_assist.describe_operation("effect_reverb")
    assert eff["category"] == "effects"
    s = audio_assist.describe_operation("sfx_whoosh")
    assert s["category"] == "sfx"


def test_describe_audio_returns_summary() -> None:
    desc = audio_assist.describe_audio(_sine())
    assert desc["summary"]
    assert "analysis" in desc


def test_describe_audio_loud_clipping() -> None:
    loud = np.full(44100, 1.5, dtype=np.float32)
    desc = audio_assist.describe_audio(loud)
    assert "clipping" in desc["details"]["loudness"]


def test_suggest_mastering_chain() -> None:
    sugg = audio_assist.suggest_mastering_chain(_sine())
    ops = {s["op"] for s in sugg["suggestions"]}
    assert "audio_normalize" in ops  # always suggested
    for s in sugg["suggestions"]:
        assert s["reason"]


def test_suggest_mastering_clipping_adds_limiter() -> None:
    loud = np.full(44100, 1.5, dtype=np.float32)
    sugg = audio_assist.suggest_mastering_chain(loud)
    ops = {s["op"] for s in sugg["suggestions"]}
    assert "apply_audio_effect" in ops


def test_execute_mastering_chain_runs() -> None:
    sig = _sine()
    out, report = audio_assist.execute_mastering_chain(sig)
    assert out.dtype == np.float32
    assert len(out) == len(sig)
    assert report["steps"]  # at least the final normalize
    assert "normalize" in report["steps"]
    assert report["peak"] > 0


def test_execute_mastering_chain_caps_peak() -> None:
    loud = np.full(44100, 1.5, dtype=np.float32)
    out, report = audio_assist.execute_mastering_chain(loud)
    # The chain should bring the clipped signal under 1.0 (limiter + normalize).
    assert float(np.max(np.abs(out))) <= 1.0
    assert "effect:limiter" in report["steps"]
