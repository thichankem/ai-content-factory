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
    tags: list[str] = Field(default_factory=list)
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
    denoise: bool = False
    denoise_strength: float = Field(default=0.8, ge=0.0, le=1.0)


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


class MediaIngestUrlRequest(BaseModel):
    """Request to ingest an external video or audio file by URL."""

    url: str
    language: str = "vi"
    extract_audio: bool = False


class AudioClipRequest(BaseModel):
    """Download any audio (by URL) and optionally cut a specific clip from it."""

    url: str = Field(min_length=1)
    start_seconds: float = Field(default=0.0, ge=0.0)
    end_seconds: float = Field(default=0.0, ge=0.0)
    language: str = "vi"


class YouTubeSearchResult(BaseModel):
    """One video returned by a YouTube search."""

    id: str
    title: str
    url: str
    duration_seconds: float | None = None
    uploader: str = ""
    thumbnail: str = ""
    description: str = ""
    view_count: int | None = None


class YouTubeSearchRequest(BaseModel):
    """Search YouTube for videos matching a query."""

    query: str = Field(min_length=1, max_length=200)
    limit: int = Field(default=8, ge=1, le=25)


class YouTubeSearchResponse(BaseModel):
    """Result of a YouTube search."""

    query: str
    count: int = 0
    results: list[YouTubeSearchResult] = Field(default_factory=list)


class YouTubeDownloadRequest(BaseModel):
    """Download a YouTube video (by URL or id) into the media library."""

    url: str = Field(min_length=1)
    language: str = "vi"
    extract_audio: bool = False
    auto_transcribe: bool = False


class YouTubeTranscriptRequest(BaseModel):
    """Get a transcript for a YouTube video by any means."""

    url: str = Field(min_length=1)
    language: str = "en"


class YouTubeTranscriptResult(BaseModel):
    """A YouTube transcript, whatever strategy produced it.

    ``source`` is ``subtitles`` (reused the video's own captions — instant, no
    model) or ``whisper`` (fell back to local faster-whisper speech-to-text).
    ``media_id`` is set only when the audio was downloaded and transcribed.
    """

    url: str
    source: str = "subtitles"
    text: str = ""
    segments: list[TranscriptSegment] = Field(default_factory=list)
    #: Whether ``segments`` carries real cue timings. A transcript can be text
    #: only (no cues parsed), and a caller that needs timings for subtitles or
    #: beat-aligned cuts must be able to tell without discovering it later.
    has_timestamps: bool = False
    media_id: str | None = None
