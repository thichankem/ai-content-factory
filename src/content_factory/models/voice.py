"""Narration: per-scene voiceover tracks and the voiceover bundle."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from .common import utcnow


class VoiceoverTrack(BaseModel):
    """A synthesized narration audio clip for one scene."""

    scene_id: str
    audio_url: str
    duration_seconds: float
    text: str


class VoiceoverBundle(BaseModel):
    """The result of synthesizing narration for every scene."""

    tracks: list[VoiceoverTrack] = Field(default_factory=list)
    engine: str = ""
    voice: str = ""
    generated_at: datetime = Field(default_factory=utcnow)
