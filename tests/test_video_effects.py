"""Tests for the pure-NumPy video frame effects."""

from __future__ import annotations

import numpy as np
import pytest

from content_factory.video_effects import (
    VideoEffectError,
    apply_frame_effect,
    effect_catalog,
    frame_effect_names,
)


@pytest.fixture
def frame() -> np.ndarray:
    """A small synthetic uint8 RGB frame."""
    arr = np.zeros((40, 60, 3), dtype=np.uint8)
    arr[..., 0] = 120
    arr[..., 1] = 140
    arr[..., 2] = 160
    arr[10:30, 10:50] = 255
    return arr


def test_all_effects_registered() -> None:
    for name in (
        "glitch",
        "shake",
        "distortion",
        "glow",
        "film_grain",
        "motion_blur",
        "particles",
        "chromatic_aberration",
        "pixelate",
        "scanlines",
        "freeze",
    ):
        assert name in frame_effect_names()


def test_unknown_effect_raises(frame: np.ndarray) -> None:
    with pytest.raises(VideoEffectError, match="Unknown effect"):
        apply_frame_effect(frame, "nope")


def test_each_effect_keeps_shape_and_dtype(frame: np.ndarray) -> None:
    for name in frame_effect_names():
        out = apply_frame_effect(frame, name, {"amount": 0.5, "seed": 1})
        assert out.shape == frame.shape
        assert out.dtype == np.uint8


def test_freeze_is_identity(frame: np.ndarray) -> None:
    out = apply_frame_effect(frame, "freeze")
    np.testing.assert_array_equal(out, frame)


def test_grain_changes_pixels(frame: np.ndarray) -> None:
    out = apply_frame_effect(frame, "film_grain", {"amount": 0.9, "seed": 1})
    assert not np.array_equal(out, frame)


def test_pixelate_blocks(frame: np.ndarray) -> None:
    out = apply_frame_effect(frame, "pixelate", {"block": 8})
    # Blocky output: each 8x8 block is uniform.
    assert np.all(out[:8, :8, 0] == out[0, 0, 0])


def test_deterministic_with_seed(frame: np.ndarray) -> None:
    a = apply_frame_effect(frame, "glitch", {"amount": 0.5, "seed": 7})
    b = apply_frame_effect(frame, "glitch", {"amount": 0.5, "seed": 7})
    np.testing.assert_array_equal(a, b)


def test_effect_catalog_has_descriptions() -> None:
    cat = effect_catalog()
    names = {e["name"] for e in cat["effects"]}
    assert "glitch" in names
    for entry in cat["effects"]:
        assert entry["description"]


def test_accepts_float_input() -> None:
    rgb = np.full((20, 20, 3), 0.5, dtype=np.float32)
    out = apply_frame_effect(rgb, "scanlines", {"amount": 0.5})
    assert out.dtype == np.uint8
    assert out.shape == (20, 20, 3)
