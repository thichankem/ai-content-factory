from __future__ import annotations

from pydantic import BaseModel, Field

from .timeline import VideoProject


class PlatformCheckRequest(BaseModel):
    platform: str
    duration_seconds: float | None = None
    aspect_ratio: str = ""
    words: int = 0
    text: str = ""


class BrandCheckRequest(BaseModel):
    dominant_colors: list[str] = Field(default_factory=list)
    fonts_used: list[str] = Field(default_factory=list)
    has_logo: bool = False
    palette: list[str] = Field(default_factory=list)
    fonts: list[str] = Field(default_factory=list)
    logo_fingerprints: list[str] = Field(default_factory=list)


class CopyrightCheckRequest(BaseModel):
    fingerprint: str
    protected: list[str] = Field(default_factory=list)


class AuditRecordRequest(BaseModel):
    actor: str = Field(min_length=1)
    action: str = Field(min_length=1)
    project_id: str | None = None
    media_id: str | None = None
    prompt: str | None = None
    detail: str | None = None


class CostCheckRequest(BaseModel):
    calls: dict[str, int] = Field(default_factory=dict)


class ViralityRequest(BaseModel):
    script: str = Field(min_length=1)
    duration_seconds: float | None = None
    hook: str | None = None


class DuckRequest(BaseModel):
    music_media_id: str
    voice_media_id: str
    out: str | None = None


class ThumbnailRequest(BaseModel):
    media_id: str
    top_k: int = Field(default=3, ge=1, le=10)
    overlays: list[str] = Field(default_factory=list)


class DedupRequest(BaseModel):
    media_ids: list[str] = Field(min_length=1)


class TimelineCommandRequest(BaseModel):
    project: VideoProject
    text: str = Field(min_length=1)


class SimplifySubtitlesRequest(BaseModel):
    captions: list[str] = Field(min_length=1)
    level: str = "basic"
