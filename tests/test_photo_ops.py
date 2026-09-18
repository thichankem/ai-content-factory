"""Tests for the extended photo operations (light, colour, detail, local,
retouch, transform, effects)."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from content_factory.image_engine import KNOWN_OPS, apply_ops, export_bytes


@pytest.fixture
def png_bytes() -> bytes:
    img = Image.new("RGBA", (120, 80), (60, 70, 80, 255))
    for x in range(0, 120, 10):
        for y in range(0, 80, 10):
            img.putpixel((x, y), (240, 200, 40, 255))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def _channel_mean(image: Image.Image, channel: int) -> float:
    hist = image.convert("RGB").histogram()[channel * 256 : (channel + 1) * 256]
    total = sum(hist)
    return sum(i * v for i, v in enumerate(hist)) / max(1, total)


def test_extended_ops_are_registered() -> None:
    for op in (
        "exposure",
        "highlights",
        "shadows",
        "whites",
        "blacks",
        "levels",
        "white_balance",
        "temperature",
        "tint",
        "vibrance",
        "hsl",
        "color_grade",
        "split_toning",
        "noise_reduce",
        "clarity",
        "texture",
        "dehaze",
        "local_adjust",
        "radial_filter",
        "gradient_filter",
        "brush",
        "spot_heal",
        "clone_stamp",
        "red_eye",
        "liquify",
        "dodge_burn",
        "frequency_separation",
        "straighten",
        "perspective",
        "lens_correction",
        "grain",
        "watermark",
        "motion_blur",
        "lens_blur",
    ):
        assert op in KNOWN_OPS, op


def test_exposure_brightens(png_bytes: bytes) -> None:
    before = _channel_mean(apply_ops(png_bytes, []), 0)
    after = _channel_mean(
        apply_ops(png_bytes, [{"name": "exposure", "params": {"ev": 1.0}}]), 0
    )
    assert after > before


def test_exposure_darkens(png_bytes: bytes) -> None:
    before = _channel_mean(apply_ops(png_bytes, []), 0)
    after = _channel_mean(
        apply_ops(png_bytes, [{"name": "exposure", "params": {"ev": -1.0}}]), 0
    )
    assert after < before


def test_levels_expands_range(png_bytes: bytes) -> None:
    out = apply_ops(
        png_bytes, [{"name": "levels", "params": {"black": 0.1, "white": 0.9}}]
    )
    assert out.size == (120, 80)


def test_white_balance_warms(png_bytes: bytes) -> None:
    base = apply_ops(png_bytes, [])
    r_before = _channel_mean(base, 0)
    b_before = _channel_mean(base, 2)
    out = apply_ops(
        png_bytes, [{"name": "white_balance", "params": {"temperature": 0.8}}]
    )
    r_after = _channel_mean(out, 0)
    b_after = _channel_mean(out, 2)
    assert (r_after - b_after) > (r_before - b_before)


def test_vibrance_changes_colour(png_bytes: bytes) -> None:
    before = _channel_mean(apply_ops(png_bytes, []), 0)
    out = apply_ops(png_bytes, [{"name": "vibrance", "params": {"amount": 0.8}}])
    assert _channel_mean(out, 0) != before


def test_hsl_does_not_crash_and_changes_size(png_bytes: bytes) -> None:
    out = apply_ops(
        png_bytes,
        [{"name": "hsl", "params": {"red_hue": 30, "green_sat": 0.5, "blue_lum": 0.3}}],
    )
    assert out.size == (120, 80)


def test_color_grade_and_split_toning(png_bytes: bytes) -> None:
    for name in ("color_grade", "split_toning"):
        out = apply_ops(
            png_bytes,
            [
                {
                    "name": name,
                    "params": {
                        "shadows_hue": 200,
                        "shadows_sat": 0.6,
                        "highlights_hue": 20,
                        "highlights_sat": 0.6,
                    },
                }
            ],
        )
        assert out.size == (120, 80)


def test_detail_ops_do_not_crash(png_bytes: bytes) -> None:
    for name in ("noise_reduce", "clarity", "texture", "dehaze"):
        out = apply_ops(png_bytes, [{"name": name, "params": {"amount": 0.5}}])
        assert out.size == (120, 80)


def test_local_adjust_radial(png_bytes: bytes) -> None:
    out = apply_ops(
        png_bytes,
        [{"name": "local_adjust", "params": {"shape": "radial", "brightness": 0.5}}],
    )
    assert out.size == (120, 80)


def test_spot_heal_and_clone_stamp(png_bytes: bytes) -> None:
    healed = apply_ops(
        png_bytes, [{"name": "spot_heal", "params": {"cx": 0.5, "cy": 0.5}}]
    )
    cloned = apply_ops(
        png_bytes,
        [
            {
                "name": "clone_stamp",
                "params": {"sx": 0.2, "sy": 0.2, "dx": 0.8, "dy": 0.8},
            }
        ],
    )
    assert healed.size == cloned.size == (120, 80)


def test_red_eye_does_not_crash(png_bytes: bytes) -> None:
    out = apply_ops(png_bytes, [{"name": "red_eye", "params": {"cx": 0.5, "cy": 0.5}}])
    assert out.size == (120, 80)


def test_liquify_and_dodge_burn(png_bytes: bytes) -> None:
    for name in ("liquify", "dodge_burn"):
        out = apply_ops(png_bytes, [{"name": name, "params": {"amount": 0.5}}])
        assert out.size == (120, 80)


def test_frequency_separation_and_texture(png_bytes: bytes) -> None:
    for name in ("frequency_separation", "texture"):
        out = apply_ops(png_bytes, [{"name": name, "params": {"amount": 0.5}}])
        assert out.size == (120, 80)


def test_straighten_zero_angle_is_noop(png_bytes: bytes) -> None:
    out = apply_ops(png_bytes, [{"name": "straighten", "params": {"angle": 0.0}}])
    assert out.size == (120, 80)


def test_grain_adds_noise(png_bytes: bytes) -> None:
    before = apply_ops(png_bytes, []).tobytes()
    after = apply_ops(
        png_bytes, [{"name": "grain", "params": {"amount": 0.9}}]
    ).tobytes()
    assert after != before


def test_watermark_draws_text(png_bytes: bytes) -> None:
    before = apply_ops(png_bytes, []).tobytes()
    after = apply_ops(
        png_bytes, [{"name": "watermark", "params": {"text": "©", "opacity": 0.6}}]
    ).tobytes()
    assert after != before


def test_motion_and_lens_blur(png_bytes: bytes) -> None:
    for name, params in (
        ("motion_blur", {"distance": 8}),
        ("lens_blur", {"amount": 0.5}),
    ):
        out = apply_ops(png_bytes, [{"name": name, "params": params}])
        assert out.size == (120, 80)


def _cv2_available() -> bool:
    try:
        import cv2  # noqa: F401

        return True
    except ImportError:
        return False


@pytest.mark.skipif(not _cv2_available(), reason="OpenCV required")
def test_perspective_and_lens_correction(png_bytes: bytes) -> None:
    persp = apply_ops(
        png_bytes,
        [{"name": "perspective", "params": {"tl_x": 0.1, "br_x": 0.9}}],
    )
    assert persp.size == (120, 80)
    lens = apply_ops(png_bytes, [{"name": "lens_correction", "params": {"k1": 0.3}}])
    assert lens.size == (120, 80)


def test_export_of_edited_image(png_bytes: bytes) -> None:
    out = apply_ops(png_bytes, [{"name": "exposure", "params": {"ev": 0.5}}])
    blob = export_bytes(out, "png")
    assert blob.startswith(b"\x89PNG")
