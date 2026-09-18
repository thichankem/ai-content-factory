"""Universal media library and content re-cook models."""

from __future__ import annotations

import enum
from datetime import datetime

from pydantic import BaseModel, Field

from .common import utcnow

# --- Universal Media Library & Content Re-Cook --------------------------------


class MediaKind(enum.StrEnum):
    """Broad classification of any uploaded media item."""

    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"
    DOCUMENT = "document"
    OTHER = "other"


class TranscriptSegment(BaseModel):
    """One timed segment of a transcription."""

    start_seconds: float
    end_seconds: float
    text: str


class MediaItem(BaseModel):
    """A file in the universal media library (video/audio/image/document)."""

    id: str
    filename: str
    kind: MediaKind
    mime: str = ""
    size_bytes: int = 0
    url: str = ""
    # Probing metadata (video/audio).
    duration_seconds: float | None = None
    width: int | None = None
    height: int | None = None
    # AI understanding.
    transcription: str = ""
    transcript_segments: list[TranscriptSegment] = Field(default_factory=list)
    text_content: str = ""
    language: str = "en"
    source: str = "upload"
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class ReCookMode(enum.StrEnum):
    """How aggressively the re-cook pipeline transforms the source."""

    CONDENSE = "condense"  # cut content down to a tighter cut
    EXPAND = "expand"  # add context / padding toward the target length
    BALANCED = "balanced"  # keep the spine, re-word and re-time


class ReCookRequest(BaseModel):
    """Options for re-cooking a media item into a new video."""

    new_title: str = ""
    language: str = "en"
    target_seconds: int = Field(default=60, ge=15, le=600)
    mode: ReCookMode = ReCookMode.BALANCED
    change_music: bool = True
    script_style: str = "viral-short"
    platform: str = "youtube"


class ReCookResult(BaseModel):
    """Outcome of a re-cook run: a brand-new project + re-cooked script."""

    media_id: str
    project_id: str
    project_name: str
    new_title: str
    mode: ReCookMode
    source_transcript: str
    script: str
    estimated_seconds: int
    status: str
    created_at: datetime = Field(default_factory=utcnow)
