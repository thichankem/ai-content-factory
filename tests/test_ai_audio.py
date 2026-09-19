"""Tests for the AI audio adapter registry (dub / voice clone)."""

from __future__ import annotations

import pytest

from content_factory import ai_audio


def test_catalog_lists_capabilities() -> None:
    cat = ai_audio.ai_audio_catalog()
    names = {c["name"] for c in cat["capabilities"]}
    assert {"dub", "voice_clone", "separate"} <= names
    for c in cat["capabilities"]:
        assert c["description"]
        assert isinstance(c["adapter"], bool)


def test_dub_requires_adapter() -> None:
    with pytest.raises(ai_audio.AiAudioError, match="adapter"):
        ai_audio.dub_audio(b"audio", "Hello", "en")


def test_voice_clone_requires_adapter() -> None:
    with pytest.raises(ai_audio.AiAudioError, match="adapter"):
        ai_audio.voice_clone(b"audio", b"ref")


def test_dub_rejects_empty_text() -> None:
    with pytest.raises(ai_audio.AiAudioError, match="target_text"):
        ai_audio.dub_audio(b"audio", "   ", "en")


def test_register_and_call_adapter() -> None:
    calls = {}

    def fake_dub(*, data: bytes, target_text: str, lang: str) -> dict:
        calls["called"] = True
        return {"dubbed": True, "lang": lang, "text": target_text}

    ai_audio.register_adapter("dub", fake_dub)
    try:
        result = ai_audio.dub_audio(b"audio", "Hi", "vi")
        assert calls.get("called") is True
        assert result["lang"] == "vi"
        assert result["text"] == "Hi"
    finally:
        ai_audio._AUDIO_ADAPTERS.pop("dub", None)


def test_catalog_reflects_adapter() -> None:
    def fake_clone(*, data: bytes, ref_voice: bytes) -> dict:
        return {"cloned": True}

    ai_audio.register_adapter("voice_clone", fake_clone)
    try:
        cat = ai_audio.ai_audio_catalog()
        vc = next(c for c in cat["capabilities"] if c["name"] == "voice_clone")
        assert vc["adapter"] is True
        assert "voice_clone" in cat["registered_adapters"]
    finally:
        ai_audio._AUDIO_ADAPTERS.pop("voice_clone", None)
