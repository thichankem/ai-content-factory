"""Tests for the non-destructive image edit session (undo / redo / history)."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from content_factory.image_engine import ImageError
from content_factory.image_voice_service import ImageVoiceStudio


@pytest.fixture
def studio(tmp_path) -> ImageVoiceStudio:
    return ImageVoiceStudio(tmp_path / "library")


def _png(color=(120, 120, 120, 255), size=(60, 60)) -> bytes:
    img = Image.new("RGBA", size, color)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def test_session_undo_redo(studio: ImageVoiceStudio) -> None:
    begun = studio.begin_image_session(_png())
    sid = begun["session_id"]
    assert begun["version"] == 0
    assert begun["can_undo"] is False

    step1 = studio.edit_image_session(
        sid, [{"name": "exposure", "params": {"ev": 1.0}}]
    )
    assert step1["version"] == 1
    assert step1["can_undo"] is True

    step2 = studio.edit_image_session(
        sid, [{"name": "grain", "params": {"amount": 0.5}}]
    )
    assert step2["version"] == 2

    undone = studio.undo_image_session(sid)
    assert undone["version"] == 1
    assert undone["can_redo"] is True

    redone = studio.redo_image_session(sid)
    assert redone["version"] == 2

    state = studio.image_session_state(sid)
    assert state["version"] == 2
    assert state["can_undo"] is True
    assert state["can_redo"] is False


def test_undo_at_start_raises(studio: ImageVoiceStudio) -> None:
    sid = studio.begin_image_session(_png())["session_id"]
    with pytest.raises(ImageError, match="Nothing to undo"):
        studio.undo_image_session(sid)


def test_redo_without_undo_raises(studio: ImageVoiceStudio) -> None:
    sid = studio.begin_image_session(_png())["session_id"]
    with pytest.raises(ImageError, match="Nothing to redo"):
        studio.redo_image_session(sid)


def test_unknown_session_raises(studio: ImageVoiceStudio) -> None:
    with pytest.raises(ImageError, match="Unknown image session"):
        studio.image_session_state("nope")


def test_new_step_truncates_redo_tail(studio: ImageVoiceStudio) -> None:
    sid = studio.begin_image_session(_png())["session_id"]
    studio.edit_image_session(sid, [{"name": "exposure", "params": {"ev": 1.0}}])
    studio.edit_image_session(sid, [{"name": "grain", "params": {"amount": 0.5}}])
    studio.undo_image_session(sid)
    # A fresh edit after undo discards the redo branch.
    studio.edit_image_session(sid, [{"name": "sharpen", "params": {"percent": 20}}])
    state = studio.image_session_state(sid)
    assert state["version"] == 2
    assert state["can_redo"] is False


def test_batch_edit_applies_to_all(studio: ImageVoiceStudio) -> None:
    result = studio.batch_edit_images(
        [_png((10, 10, 10)), _png((200, 200, 200))],
        ops=[{"name": "exposure", "params": {"ev": 0.5}}],
    )
    assert result["count"] == 2
    assert len(result["results"]) == 2


def test_analyze_and_suggest(studio: ImageVoiceStudio) -> None:
    analysis = studio.analyze_image_bytes(_png((20, 20, 20)))
    assert analysis["summary"]
    suggestions = studio.suggest_image_edits(_png((20, 20, 20)))
    assert "suggestions" in suggestions


def test_op_catalog_and_describe(studio: ImageVoiceStudio) -> None:
    cat = studio.image_op_catalog()
    assert "light" in cat["categories"]
    info = studio.describe_image_op("exposure")
    assert info["name"] == "exposure"
