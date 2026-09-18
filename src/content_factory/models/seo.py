"""Request models for the SEO scoring, optimisation and testing endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..seo import METRIC_NAMES, AbArm, CompetitorVideo, Engagement, Pack


class SeoEngagementInput(BaseModel):
    """Measured results of an already published video."""

    impressions: int = Field(default=0, ge=0)
    views: int = Field(default=0, ge=0)
    likes: int = Field(default=0, ge=0)
    comments: int = Field(default=0, ge=0)
    shares: int = Field(default=0, ge=0)
    saves: int = Field(default=0, ge=0)
    follows: int = Field(default=0, ge=0)
    watch_time_seconds: float = Field(default=0.0, ge=0.0)
    average_view_seconds: float | None = Field(default=None, ge=0.0)
    completion_rate: float | None = Field(default=None, ge=0.0, le=1.5)

    def to_engine(self) -> Engagement:
        return Engagement(
            impressions=self.impressions,
            views=self.views,
            likes=self.likes,
            comments=self.comments,
            shares=self.shares,
            saves=self.saves,
            follows=self.follows,
            watch_time_seconds=self.watch_time_seconds,
            average_view_seconds=self.average_view_seconds,
            completion_rate=self.completion_rate,
        )


class SeoPackInput(BaseModel):
    """The publish pack under test (metadata, structure and settings)."""

    title: str = ""
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    hashtags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    script: str = ""
    hook: str = ""
    duration_seconds: float | None = Field(default=None, ge=0.0)
    aspect_ratio: str = ""
    thumbnail_present: bool | None = None
    thumbnail_text: str = ""
    on_screen_text: list[str] = Field(default_factory=list)
    has_captions: bool | None = None
    caption_source: str = ""
    has_chapters: bool = False
    chapter_count: int = Field(default=0, ge=0)
    has_end_screen: bool | None = None
    playlist: str | None = None
    sound: str = ""
    sound_trending: bool | None = None
    beat_synced: bool | None = None
    bpm: int | None = None
    cuts_per_minute: float | None = Field(default=None, ge=0.0)
    loop_friendly: bool | None = None
    intro_seconds: float | None = Field(default=None, ge=0.0)
    text_in_safe_zone: bool | None = None
    publish_hour: int | None = Field(default=None, ge=0, le=23)
    audience_hours: list[int] = Field(default_factory=list)
    watermark: bool | None = None
    comment_prompt: bool = False
    series_part: int | None = Field(default=None, ge=1)
    duet_stitch_enabled: bool | None = None
    channel: str = ""
    language: str = "vi"
    engagement: SeoEngagementInput | None = None

    def to_engine(self) -> Pack:
        """Convert to the engine's frozen pack."""
        return Pack(
            title=self.title,
            description=self.description,
            tags=tuple(self.tags),
            hashtags=tuple(self.hashtags),
            keywords=tuple(self.keywords),
            script=self.script,
            hook=self.hook,
            duration_seconds=self.duration_seconds,
            aspect_ratio=self.aspect_ratio,
            thumbnail_present=self.thumbnail_present,
            thumbnail_text=self.thumbnail_text,
            on_screen_text=tuple(self.on_screen_text),
            has_captions=self.has_captions,
            caption_source=self.caption_source,
            has_chapters=self.has_chapters,
            chapter_count=self.chapter_count,
            has_end_screen=self.has_end_screen,
            playlist=self.playlist,
            sound=self.sound,
            sound_trending=self.sound_trending,
            beat_synced=self.beat_synced,
            bpm=self.bpm,
            cuts_per_minute=self.cuts_per_minute,
            loop_friendly=self.loop_friendly,
            intro_seconds=self.intro_seconds,
            text_in_safe_zone=self.text_in_safe_zone,
            publish_hour=self.publish_hour,
            audience_hours=tuple(self.audience_hours),
            watermark=self.watermark,
            comment_prompt=self.comment_prompt,
            series_part=self.series_part,
            duet_stitch_enabled=self.duet_stitch_enabled,
            channel=self.channel,
            language=self.language,
            engagement=self.engagement.to_engine() if self.engagement else None,
        )


#: Platform names a request may target, plus the "all" shorthand.
SEO_PLATFORMS: tuple[str, ...] = ("youtube", "youtube_shorts", "tiktok", "all")
#: Metrics the A/B tools accept.
SEO_METRICS: tuple[str, ...] = METRIC_NAMES


class SeoScoreRequest(BaseModel):
    """Score one pack, optionally on every supported platform."""

    platform: str = "youtube"
    pack: SeoPackInput = Field(default_factory=SeoPackInput)


class SeoOptimizeRequest(BaseModel):
    """Rewrite a pack for maximum score and report the measured gain."""

    platform: str = "youtube"
    pack: SeoPackInput = Field(default_factory=SeoPackInput)


class SeoProjectScoreRequest(BaseModel):
    """Score the pack a project would actually publish."""

    platform: str = "youtube"
    keywords: list[str] = Field(default_factory=list)
    publish_hour: int | None = Field(default=None, ge=0, le=23)
    audience_hours: list[int] = Field(default_factory=list)
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    hashtags: list[str] = Field(default_factory=list)
    title: str | None = None
    engagement: SeoEngagementInput | None = None


class SeoAbPlanRequest(BaseModel):
    """Size an A/B test for a detectable lift."""

    metric: str = "ctr"
    baseline_rate: float = Field(gt=0.0, lt=1.0)
    relative_lift: float = Field(default=0.15, gt=0.0, lt=5.0)
    daily_traffic: int | None = Field(default=None, gt=0)
    arms: int = Field(default=2, ge=2, le=6)
    alpha: float = Field(default=0.05, gt=0.0, lt=0.5)
    power: float = Field(default=0.8, gt=0.0, le=1.0)


class AbArmInput(BaseModel):
    """One arm of an A/B test."""

    name: str
    impressions: int = Field(default=0, ge=0)
    clicks: int = Field(default=0, ge=0)
    views: int = Field(default=0, ge=0)
    completions: int = Field(default=0, ge=0)
    saves: int = Field(default=0, ge=0)
    shares: int = Field(default=0, ge=0)
    follows: int = Field(default=0, ge=0)
    watch_time_seconds: float = Field(default=0.0, ge=0.0)
    mean_value: float | None = None
    sd_value: float | None = Field(default=None, ge=0.0)

    def to_engine(self) -> AbArm:
        return AbArm(**self.model_dump())


class SeoAbEvaluateRequest(BaseModel):
    """Test whether one variant really beats another."""

    metric: str = "ctr"
    arms: list[AbArmInput] = Field(min_length=2)
    alpha: float = Field(default=0.05, gt=0.0, lt=0.5)
    relative_lift: float = Field(default=0.15, gt=0.0, lt=5.0)


class CompetitorVideoInput(BaseModel):
    """One competitor video in the niche corpus."""

    title: str
    views: int = Field(default=0, ge=0)
    channel: str = ""
    subscribers: int = Field(default=0, ge=0)
    days_old: int | None = Field(default=None, ge=0)
    duration_seconds: float | None = Field(default=None, ge=0.0)

    def to_engine(self) -> CompetitorVideo:
        return CompetitorVideo(**self.model_dump())


class SeoKeywordRequest(BaseModel):
    """Rank phrases by demand vs competition and find winning phrasings."""

    keywords: list[str] = Field(min_length=1)
    competitors: list[CompetitorVideoInput] = Field(default_factory=list)
    pack: SeoPackInput | None = None


class CalibrateObservation(BaseModel):
    """One published video: its signal scores and its real outcome."""

    signals: dict[str, float] = Field(default_factory=dict)
    outcome: float


class SeoCalibrateRequest(BaseModel):
    """Learn which signals actually predict this channel's results."""

    platform: str = "youtube"
    outcome: str = "views_per_day"
    observations: list[CalibrateObservation] = Field(default_factory=list)
