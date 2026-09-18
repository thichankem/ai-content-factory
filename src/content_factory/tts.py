"""Text-to-speech engine for narration voiceovers.

Primary engine is Microsoft Edge's neural voices via ``edge-tts`` (free,
natural, 100+ locales including Vietnamese); ``gTTS`` is used as a fast,
dependency-light fallback when Edge is unreachable. Every provider returns
MP3 bytes plus an accurate duration (measured with mutagen) so the video
scenes can be synchronized perfectly to the narration.
"""

from __future__ import annotations

import io
import logging
from typing import Protocol

from .config import Settings

logger = logging.getLogger("content_factory.tts")

# Locale -> preferred neural voice (female unless noted).
_VOICES: dict[str, str] = {
    "vi": "vi-VN-HoaiMyNeural",
    "en": "en-US-JennyNeural",
    "fr": "fr-FR-DeniseNeural",
    "de": "de-DE-KatjaNeural",
    "es": "es-ES-ElviraNeural",
    "ja": "ja-JP-NanamiNeural",
    "ko": "ko-KR-SunHiNeural",
    "zh": "zh-CN-XiaoxiaoNeural",
    "pt": "pt-BR-FranciscaNeural",
    "ru": "ru-RU-SvetlanaNeural",
    "it": "it-IT-ElsaNeural",
    "nl": "nl-NL-ColetteNeural",
    "pl": "pl-PL-ZofiaNeural",
    "tr": "tr-TR-EmelNeural",
    "id": "id-ID-GadisNeural",
    "th": "th-TH-PremwadeeNeural",
}


def resolve_voice(language: str) -> str:
    """Map a language code to a neural voice short name."""
    lang = (language or "en").split("-")[0].lower()
    return _VOICES.get(lang, _VOICES["en"])


def mp3_duration(data: bytes) -> float:
    """Return the duration in seconds of an MP3 byte string."""
    try:
        from mutagen.mp3 import MP3

        info = MP3(io.BytesIO(data)).info
        return float(info.length) if info is not None else 0.0
    except Exception:
        return 0.0


class TTSProvider(Protocol):
    """Interface every speech synthesizer implements."""

    name: str

    async def synthesize(self, text: str, language: str) -> bytes: ...


class EdgeTTSProvider:
    """Microsoft Edge neural voices (highest quality)."""

    name = "edge-tts"

    def __init__(
        self, voice: str | None = None, rate: str = "+0%", pitch: str = "+0Hz"
    ) -> None:
        self._voice = voice
        self._rate = rate
        self._pitch = pitch

    async def synthesize(self, text: str, language: str) -> bytes:
        import edge_tts

        voice = self._voice or resolve_voice(language)
        communicate = edge_tts.Communicate(
            text, voice, rate=self._rate, pitch=self._pitch
        )
        buffer = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buffer.write(chunk["data"])
        data = buffer.getvalue()
        if not data:
            raise RuntimeError("edge-tts returned no audio")
        return data


class GTTSProvider:
    """Google Translate TTS — fast fallback, plainer voice."""

    name = "gtts"

    async def synthesize(self, text: str, language: str) -> bytes:
        from gtts import gTTS  # type: ignore[import-untyped]

        lang = (language or "en").split("-")[0].lower()
        buffer = io.BytesIO()
        gTTS(text=text, lang=lang).write_to_fp(buffer)
        data = buffer.getvalue()
        if not data:
            raise RuntimeError("gTTS returned no audio")
        return data


class TTSEngine:
    """Routes synthesis to the configured provider with graceful fallback."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._voice = settings.tts_voice or None
        self._rate = settings.tts_rate

    async def synthesize(
        self, text: str, language: str, pitch: float = 1.0
    ) -> tuple[bytes, float, str]:
        """Return ``(audio_bytes, duration_seconds, engine_name)``."""
        pitch_hz = _pitch_to_hz(pitch)
        providers: list[TTSProvider]
        if self._settings.tts_engine == "gtts":
            providers = [GTTSProvider()]
        else:
            providers = [
                EdgeTTSProvider(voice=self._voice, rate=self._rate, pitch=pitch_hz),
                GTTSProvider(),
            ]

        last_error: Exception | None = None
        for provider in providers:
            try:
                data = await provider.synthesize(text, language)
                duration = mp3_duration(data) or self._estimate_duration(text)
                return data, duration, provider.name
            except Exception as exc:
                last_error = exc
                logger.warning("TTS provider %s failed: %s", provider.name, exc)
        raise RuntimeError(f"All TTS providers failed: {last_error}")

    @staticmethod
    def _estimate_duration(text: str) -> float:
        # ~14 chars per second is a reasonable speaking-rate heuristic.
        return max(1.0, len(text or "") / 14.0)


def _pitch_to_hz(pitch: float) -> str:
    """Convert a 0.5–2.0 multiplier into edge-tts Hz notation.

    edge-tts only accepts a signed whole number of Hz (``+0Hz``, ``-24Hz``);
    a fractional value such as ``+0.0Hz`` is rejected outright, which used to
    fail every scene whose pitch sat at the neutral default.
    """
    semitones = round((pitch - 1.0) * 12.0)
    return f"{semitones:+d}Hz"
