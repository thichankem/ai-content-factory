"""Multi-format campaign fan-out: shorts, prompt packs, ratios."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .common import utcnow


class HybridAssetType(enum.StrEnum):
    """Visual asset classification for hybrid documentary production."""

    AI_RECONSTRUCTION = "ai_reconstruction"  # Kling / Veo / Wan 2.1
    HISTORICAL_PHOTO = "historical_photo"  # Archival photo / Public domain
    DYNAMIC_MAP = "dynamic_map"  # Route map / Geo animation
    DECLASSIFIED_DOC = "declassified_doc"  # Newspapers / Archives / Dossiers
    TECHNICAL_DIAGRAM = "technical_diagram"  # Cross-section / Schematics
    KINETIC_MOTION = "kinetic_motion"  # Typography / Infographics


class HybridAssetRatio(BaseModel):
    """Target percentage allocation to ensure historical credibility."""

    ai_reconstruction: int = 30
    historical_photo: int = 20
    dynamic_map: int = 15
    declassified_doc: int = 15
    technical_diagram: int = 10
    kinetic_motion: int = 10


class ShortsVariant(BaseModel):
    """A standalone vertical short video generated from the master topic."""

    id: str
    title: str
    angle: str
    hook: str
    target_duration_seconds: int = 45
    script: str
    hook_type: str = "curiosity_gap"
    scenes: list[dict[str, Any]] = Field(default_factory=list)
    video_prompts: list[str] = Field(default_factory=list)
    image_prompts: list[str] = Field(default_factory=list)
    voiceover_tone: str = "dramatic_suspense"
    call_to_action: str = ""


class PromptPack(BaseModel):
    """Optimized prompts for 3rd-party generative engines."""

    kling_veo_prompts: list[dict[str, str]] = Field(default_factory=list)
    midjourney_prompts: list[dict[str, str]] = Field(default_factory=list)
    suno_prompts: list[dict[str, str]] = Field(default_factory=list)
    elevenlabs_settings: dict[str, Any] = Field(default_factory=dict)


class MultiFormatCampaign(BaseModel):
    """Master production campaign: 1 Topic -> 1 YouTube Long + 5-10 Shorts."""

    id: str
    project_id: str
    master_topic: str
    youtube_script: str
    youtube_duration_target_seconds: int = 600  # 8-12 minutes default
    youtube_story_structure: dict[str, str] = Field(default_factory=dict)
    youtube_scenes: list[dict[str, Any]] = Field(default_factory=list)
    youtube_titles: list[str] = Field(default_factory=list)  # 5x viral titles
    youtube_description: str = ""
    youtube_chapters: list[dict[str, str]] = Field(default_factory=list)
    tiktok_hooks: list[str] = Field(default_factory=list)  # 10x retention hooks
    thumbnail_prompts: list[str] = Field(default_factory=list)
    shorts: list[ShortsVariant] = Field(default_factory=list)
    asset_ratio: HybridAssetRatio = Field(default_factory=HybridAssetRatio)
    prompt_pack: PromptPack = Field(default_factory=PromptPack)
    fact_check_summary: str = ""
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class CampaignGenerateRequest(BaseModel):
    """Options for generating a multi-format campaign."""

    shorts_count: int = Field(default=5, ge=1, le=10)
    youtube_target_minutes: int = Field(default=10, ge=5, le=20)
    include_prompts: bool = True


class ShortsUpdateRequest(BaseModel):
    """Payload for editing a single short in the campaign."""

    title: str | None = None
    script: str | None = None
    hook: str | None = None
    call_to_action: str | None = None
