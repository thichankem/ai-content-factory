"""Tests for the Photoshop-style image engine (real pixels, real PIL)."""

from __future__ import annotations

import base64
import io

import pytest
from PIL import Image

from content_factory.image_engine import (
    KNOWN_FILTERS,
    KNOWN_OPS,
    ImageError,
    apply_ops,
    export_bytes,
    load_image,
    remove_background,
)


@pytest.fixture
def png_bytes() -> bytes:
    img = Image.new("RGBA", (400, 300), (40, 50, 70, 255))
    for x in range(0, 400, 20):
        for y in range(0, 300, 20):
            img.putpixel((x, y), (250, 200, 40, 255))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def test_known_ops_and_filters_are_documented() -> None:
    for op in (
        "resize",
        "crop",
        "rotate",
        "flip",
        "tone",
        "curves",
        "color_balance",
        "filter",
        "vignette",
        "blur",
        "sharpen",
        "text",
        "padding",
    ):
        assert op in KNOWN_OPS
    expected_filters = {"grayscale", "sepia", "noir", "vintage", "cool", "warm"}
    assert expected_filters <= set(KNOWN_FILTERS)


def test_pipeline_applies_ops_in_order(png_bytes: bytes) -> None:
    out = apply_ops(
        png_bytes,
        [
            {"name": "tone", "params": {"brightness": 1.2}},
            {"name": "filter", "params": {"preset": "noir"}},
            {"name": "resize", "params": {"width": 200, "height": 150}},
        ],
    )
    assert out.size == (200, 150)


def test_crop_and_rotate(png_bytes: bytes) -> None:
    cropped = apply_ops(
        png_bytes,
        [
            {
                "name": "crop",
                "params": {"left": 10, "top": 10, "width": 100, "height": 80},
            },
        ],
    )
    assert cropped.size == (100, 80)
    rotated = apply_ops(png_bytes, [{"name": "rotate", "params": {"degrees": 90}}])
    assert rotated.size == (300, 400)


def test_text_draws_pixels(png_bytes: bytes) -> None:
    before = apply_ops(png_bytes, [])
    after = apply_ops(
        png_bytes,
        [
            {"name": "text", "params": {"text": "HI", "size": 60}},
        ],
    )
    assert list(after.getdata()) != list(before.getdata())


def test_unknown_op_raises_with_helpful_message(png_bytes: bytes) -> None:
    with pytest.raises(ImageError, match="Unknown op 'magic'"):
        apply_ops(png_bytes, [{"name": "magic"}])


def test_garbage_bytes_raise(png_bytes: bytes) -> None:
    with pytest.raises(ImageError, match="Cannot decode"):
        apply_ops(b"definitely not an image", [])
    with pytest.raises(ImageError, match="Empty"):
        apply_ops(b"", [])


def test_auto_enhance_returns_same_size(png_bytes: bytes) -> None:
    out = apply_ops(png_bytes, [{"name": "auto_enhance"}])
    assert out.size == (400, 300)


def test_remove_background_makes_border_transparent() -> None:
    # solid green image, auto key -> whole image becomes transparent
    img = Image.new("RGBA", (50, 50), (20, 200, 60, 255))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    out = remove_background(
        load_image(buf.getvalue()),
        type("Op", (), {"num": lambda self, k, d: 0.3, "params": {"color": "auto"}})(),
    )
    alphas = [px[3] for px in out.getdata()]
    assert max(alphas) == 0


def test_export_formats(png_bytes: bytes) -> None:
    img = apply_ops(png_bytes, [])
    for fmt, magic in (("png", b"PNG"), ("jpeg", b"JFIF"), ("webp", b"WEBP")):
        blob = export_bytes(img, fmt)
        assert len(blob) > 100
        assert magic in blob


def test_padding_letterboxes_to_exact_canvas(png_bytes: bytes) -> None:
    out = apply_ops(
        png_bytes,
        [
            {"name": "padding", "params": {"width": 1080, "height": 1920}},
        ],
    )
    assert out.size == (1080, 1920)


@pytest.mark.parametrize("method", ["telea", "navier-stokes"])
def test_inpaint_removes_mark_and_preserves_unmasked_pixels(method: str) -> None:
    pytest.importorskip("cv2")
    img = Image.new("RGBA", (32, 32), (120, 150, 180, 100))
    mask = Image.new("L", img.size, 0)
    for x in range(14, 18):
        for y in range(14, 18):
            img.putpixel((x, y), (0, 0, 0, 100))
            mask.putpixel((x, y), 255)
    result = apply_ops(
        export_bytes(img),
        [
            {
                "name": "inpaint",
                "params": {
                    "mask_b64": base64.b64encode(export_bytes(mask)).decode(),
                    "method": method,
                },
            }
        ],
    )
    assert result.size == img.size
    assert result.getchannel("A").tobytes() == img.getchannel("A").tobytes()
    assert result.getpixel((15, 15))[0] > 100
    for x in range(32):
        for y in range(32):
            if mask.getpixel((x, y)) == 0:
                assert result.getpixel((x, y)) == img.getpixel((x, y))
    assert "inpaint" in KNOWN_OPS


@pytest.mark.parametrize(
    ("params", "message"),
    [
        ({}, "mask_b64"),
        ({"mask_b64": "!!!"}, "valid base64"),
        ({"mask_b64": "bm90IGFuIGltYWdl"}, "decode mask"),
        ({"method": "magic"}, "method"),
        ({"radius": float("nan")}, "radius"),
        ({"radius": 0}, "radius"),
        ({"radius": 51}, "radius"),
    ],
)
def test_inpaint_invalid_parameters(
    png_bytes: bytes, params: dict, message: str
) -> None:
    with pytest.raises(ImageError, match=message):
        apply_ops(png_bytes, [{"name": "inpaint", "params": params}])


@pytest.mark.parametrize("fill", [0, 255])
def test_inpaint_empty_and_full_masks(fill: int) -> None:
    pytest.importorskip("cv2")
    img = Image.new("RGBA", (20, 20), (100, 140, 180, 90))
    encoded = base64.b64encode(export_bytes(Image.new("L", img.size, fill))).decode()
    ops = [{"name": "inpaint", "params": {"mask_b64": encoded}}]
    if fill:
        with pytest.raises(ImageError, match="unselected"):
            apply_ops(export_bytes(img), ops)
    else:
        assert apply_ops(export_bytes(img), ops).tobytes() == img.tobytes()


def test_inpaint_rejects_mismatched_mask(png_bytes: bytes) -> None:
    encoded = base64.b64encode(export_bytes(Image.new("L", (2, 2), 0))).decode()
    with pytest.raises(ImageError, match="dimensions"):
        apply_ops(png_bytes, [{"name": "inpaint", "params": {"mask_b64": encoded}}])
