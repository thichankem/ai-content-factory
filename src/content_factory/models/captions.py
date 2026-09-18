"""Auto-caption models: word-level cues, karaoke templates, safe zones.

Mirrors ``docs/SPEC-VIDEO-EDITING.md`` §2.5. The studio renders animated
captions from the *word timings* a transcript carries, so the model keeps the
cue list and the template apart: a template changes how a cue looks, never
when it appears.
"""

from __future__ import annotations

import enum
from typing import Literal

from pydantic import BaseModel, Field


class CaptionTemplateType(enum.StrEnum):
    """The viral caption templates the studio can draw."""

    TRENDING = "trending"
    EMPHASIS = "emphasis"
    GLOW = "glow"
    EMOJI = "emoji"
    MONOLINE = "monoline"
    MULTILINE = "multiline"


class CaptionWordCue(BaseModel):
    """One word with its window on the timeline."""

    word: str
    start_time: float = Field(ge=0.0)
    end_time: float = Field(ge=0.0)
    is_highlighted: bool = False


class CaptionSegment(BaseModel):
    """One subtitle line, split into word-level cues for karaoke animation."""

    id: str
    start_time: float = Field(ge=0.0)
    end_time: float = Field(ge=0.0)
    text: str
    words: list[CaptionWordCue] = Field(default_factory=list)
    preset_style: CaptionTemplateType = CaptionTemplateType.TRENDING
    text_color: str = "#ffffff"
    bg_box_color: str | None = "#ef4444"
    glow_color: str | None = None


class AutoCaptionsRequest(BaseModel):
    """Ask for styled captions over a project's narration."""

    project_id: str
    language: str = "vi"
    highlight_keywords: bool = True
    max_words_per_line: int = Field(default=4, ge=1, le=12)
    template_id: CaptionTemplateType = CaptionTemplateType.TRENDING


class AutoCaptionsResponse(BaseModel):
    """The caption track the studio can draw, plus what it was derived from."""

    segments: list[CaptionSegment] = Field(default_factory=list)
    language: str = "vi"
    source: Literal["transcript", "narration", "script"] = "transcript"
    engine: str = ""
