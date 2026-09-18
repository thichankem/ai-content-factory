from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

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
    """A fingerprint to clear, or a batch of asset ids to clear at once.

    ``fingerprint`` is the canonical single-check field. ``asset_ids`` is the
    batch spelling the web clients send: each id is treated as a fingerprint and
    reported on individually, so a UI can tick a list of assets without knowing
    how fingerprints are computed.
    """

    fingerprint: str | None = None
    asset_ids: list[str] = Field(default_factory=list)
    protected: list[str] = Field(default_factory=list)

    @property
    def candidates(self) -> list[str]:
        """Every fingerprint to check, in order, without duplicates."""
        seen: list[str] = []
        for value in (self.fingerprint, *self.asset_ids):
            if value and value not in seen:
                seen.append(value)
        return seen

    @model_validator(mode="after")
    def _require_a_candidate(self) -> CopyrightCheckRequest:
        if not self.candidates:
            raise ValueError("provide 'fingerprint' or 'asset_ids'")
        return self


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
    """A script to score.

    Both spellings are accepted on purpose: ``script`` is the canonical field the
    CLI, the pipeline and the agent tools use, while ``script_text`` is what both
    web clients send. Accepting one spelling and rejecting the other is the kind
    of contract drift that silently 422s a working UI, so both are valid and
    exactly one is required.
    """

    script: str | None = None
    script_text: str | None = None
    topic: str | None = None
    duration_seconds: float | None = None
    hook: str | None = None

    @property
    def text(self) -> str:
        """The script body, whichever field carried it."""
        return (self.script or self.script_text or "").strip()

    @model_validator(mode="after")
    def _require_a_script(self) -> ViralityRequest:
        if not self.text:
            raise ValueError("provide 'script' (or its alias 'script_text')")
        return self


class DuckRequest(BaseModel):
    music_media_id: str
    voice_media_id: str
    out: str | None = None


class ThumbnailRequest(BaseModel):
    """What to draw thumbnail candidates from.

    The source is resolved in order: an explicit ``media_id``, then a
    ``media_path`` on disk (what the web clients can supply from a preview), then
    ``project_id``'s own source media, and finally the most recently uploaded
    video asset. The last two exist so the UI can ask for thumbnails while the
    operator is looking at a project without first having to know a media id; a
    request that resolves to nothing returns no candidates rather than a 422.
    """

    media_id: str | None = None
    media_path: str | None = None
    project_id: str | None = None
    topic: str = ""
    style: str = ""
    top_k: int = Field(default=3, ge=1, le=10)
    count: int | None = Field(default=None, ge=1, le=10)
    overlays: list[str] = Field(default_factory=list)

    @property
    def limit(self) -> int:
        """How many candidates to draw: ``count`` (client spelling) or ``top_k``."""
        return self.count or self.top_k


class DedupRequest(BaseModel):
    media_ids: list[str] = Field(min_length=1)


class TimelineCommandRequest(BaseModel):
    project: VideoProject
    text: str = Field(min_length=1)


class SimplifySubtitlesRequest(BaseModel):
    captions: list[str] = Field(min_length=1)
    level: str = "basic"
