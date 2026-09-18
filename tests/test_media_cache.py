"""Media transcription is memoized by content hash via the ContentCache."""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

from content_factory.cache import ContentCache
from content_factory.media import MediaLibrary


def _install_fake_whisper() -> MagicMock:
    """Install a fake faster_whisper module that returns fixed segments."""
    fake = MagicMock()
    seg = MagicMock()
    seg.start = 0.0
    seg.end = 1.2
    seg.text = "hello world"
    fake.WhisperModel.return_value.transcribe.return_value = ([seg], None)
    module = types.ModuleType("faster_whisper")
    module.WhisperModel = fake.WhisperModel
    sys.modules["faster_whisper"] = module
    return fake


def _clear_transcription(item) -> None:
    """Simulate a fresh read: forget the in-memory transcript so the guard passes."""
    item.transcription = ""
    item.transcript_segments = []


def test_transcribe_is_cached_across_calls(tmp_path) -> None:
    fake = _install_fake_whisper()
    cache = ContentCache(tmp_path / "cache")
    lib = MediaLibrary(tmp_path / "media", cache=cache)
    item = lib.upload("clip.mp4", b"\x00\x01\x02video-bytes")

    lib.transcribe(item.id, language="en")
    assert fake.WhisperModel.call_count == 1
    assert item.transcription == "hello world"

    # Forget the transcript; the cache must prevent re-running the model.
    _clear_transcription(item)
    lib.transcribe(item.id, language="en")
    assert fake.WhisperModel.call_count == 1


def test_transcribe_recomputes_for_different_language(tmp_path) -> None:
    fake = _install_fake_whisper()
    cache = ContentCache(tmp_path / "cache")
    lib = MediaLibrary(tmp_path / "media", cache=cache)
    item = lib.upload("clip.mp4", b"video-bytes")

    lib.transcribe(item.id, language="en")
    _clear_transcription(item)
    lib.transcribe(item.id, language="vi")
    assert fake.WhisperModel.call_count == 2


def test_transcribe_without_cache_runs_each_time(tmp_path) -> None:
    fake = _install_fake_whisper()
    lib = MediaLibrary(tmp_path / "media")  # no cache
    item = lib.upload("clip.mp4", b"video-bytes")

    lib.transcribe(item.id, language="en")
    _clear_transcription(item)
    lib.transcribe(item.id, language="en")
    assert fake.WhisperModel.call_count == 2
