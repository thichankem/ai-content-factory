"""Video timeline: scenes, effects, keyframes, markers, render plan."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from .common import (
    IssueSeverity,
    utcnow,
)


class VideoTransition(enum.StrEnum):
    """Transition effect between scenes."""

    CUT = "cut"
    FADE = "fade"
    SLIDE = "slide"
    ZOOM = "zoom"
    WIPE = "wipe"
    CIRCLE = "circle"
    DISSOLVE = "dissolve"


class TextPosition(enum.StrEnum):
    """Vertical placement of on-screen text."""

    TOP = "top"
    CENTER = "center"
    BOTTOM = "bottom"


class VideoFilter(enum.StrEnum):
    """One-click color / treatment filters (Shotcut-style)."""

    NONE = "none"
    GRAYSCALE = "grayscale"
    SEPIA = "sepia"
    INVERT = "invert"
    BLUR = "blur"
    VIGNETTE = "vignette"
    WARM = "warm"
    COOL = "cool"
    CONTRAST = "contrast"
    BRIGHTNESS = "brightness"


class KenBurns(enum.StrEnum):
    """Pan/zoom motion on a static background (OpenShot-style)."""

    NONE = "none"
    PAN_LEFT = "pan-left"
    PAN_RIGHT = "pan-right"
    ZOOM_IN = "zoom-in"
    ZOOM_OUT = "zoom-out"


class TextStyle(enum.StrEnum):
    """Text presentation presets (CapCut-style)."""

    NORMAL = "normal"
    TITLE = "title"
    SUBTITLE = "subtitle"
    CAPTION = "caption"
    NEON = "neon"
    OUTLINE = "outline"
    SHADOW = "shadow"


class EntranceEffect(enum.StrEnum):
    """Entrance animation for a scene's text (keyframe-style)."""

    NONE = "none"
    FADE = "fade"
    SLIDE_UP = "slide-up"
    ZOOM = "zoom"
    BOUNCE = "bounce"
    BLUR_IN = "blur-in"


class ExitEffect(enum.StrEnum):
    """Exit animation for a scene's text."""

    NONE = "none"
    FADE = "fade"
    SLIDE_DOWN = "slide-down"
    ZOOM = "zoom"


class SceneEffect(enum.StrEnum):
    """Additional visual effect overlays (CapCut-style)."""

    NONE = "none"
    GLITCH = "glitch"
    PIXELATE = "pixelate"
    SCANLINES = "scanlines"
    FILM_GRAIN = "film-grain"
    OLD_FILM = "old-film"
    DREAMY = "dreamy"
    SHARPEN = "sharpen"
    MOSAIC = "mosaic"


class ColorGrade(enum.StrEnum):
    """One-click cinematic color grades (LUT-style)."""

    NONE = "none"
    TEAL_ORANGE = "teal-orange"
    NOIR = "noir"
    VINTAGE = "vintage"
    CYBERPUNK = "cyberpunk"
    PASTEL = "pastel"


class SceneMotion(BaseModel):
    """Keyframe-style motion animation for a scene (neutral → target)."""

    scale: float = Field(default=1.0, ge=0.5, le=2.0)
    rotation: float = Field(default=0.0, ge=-180.0, le=180.0)
    opacity: float = Field(default=1.0, ge=0.0, le=1.0)
    pos_x: float = Field(default=0.0, ge=-100.0, le=100.0)
    pos_y: float = Field(default=0.0, ge=-100.0, le=100.0)
    easing: str = "ease-in-out"


class Keyframe(BaseModel):
    """One point on a scene's motion track.

    ``at`` is a fraction of the scene's duration (0.0 = first frame,
    1.0 = last frame), so a keyframe track stays valid when the scene is
    retimed. An empty track falls back to :class:`SceneMotion`.
    """

    at: float = Field(default=0.0, ge=0.0, le=1.0)
    scale: float = Field(default=1.0, ge=0.5, le=2.0)
    rotation: float = Field(default=0.0, ge=-180.0, le=180.0)
    opacity: float = Field(default=1.0, ge=0.0, le=1.0)
    pos_x: float = Field(default=0.0, ge=-100.0, le=100.0)
    pos_y: float = Field(default=0.0, ge=-100.0, le=100.0)
    easing: str = "ease-in-out"


class TimelineMarker(BaseModel):
    """A labelled point on the timeline (beat, cue, chapter, note)."""

    id: str
    time_seconds: float = Field(ge=0.0)
    label: str = ""
    color: str = "#f59e0b"


class OverlayPosition(enum.StrEnum):
    """Placement of an emoji/sticker overlay."""

    TOP_LEFT = "top-left"
    TOP_RIGHT = "top-right"
    CENTER = "center"
    BOTTOM_LEFT = "bottom-left"
    BOTTOM_RIGHT = "bottom-right"


class VideoScene(BaseModel):
    """A single editable scene in the video project.

    Two spellings of the same facts live here on purpose. ``duration_seconds``
    and ``image_url`` are the canonical stored fields; ``duration`` and
    ``asset_url`` are the names the web editor binds to, and ``index`` is the
    scene's position, which callers previously had to infer from list order.
    A timeline that reads a field the payload never carried renders ``NaN``
    widths, so the editor's names are projected rather than assumed.
    """

    id: str
    label: str
    text: str
    narration: str | None = None
    duration_seconds: float = Field(default=3.0, ge=0.5, le=60.0)
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    background: str = "#1a1d27"
    image_url: str | None = None
    video_url: str | None = None
    asset_type: str | None = None
    source_attribution: str | None = None
    transition: VideoTransition = VideoTransition.FADE
    text_position: TextPosition = TextPosition.CENTER
    text_color: str = "#ffffff"
    font_size: int = Field(default=48, ge=16, le=140)
    text_style: TextStyle = TextStyle.NORMAL
    filter: VideoFilter = VideoFilter.NONE
    ken_burns: KenBurns = KenBurns.NONE
    entrance: EntranceEffect = EntranceEffect.FADE
    exit: ExitEffect = ExitEffect.NONE
    motion: SceneMotion | None = None
    effect: SceneEffect = SceneEffect.NONE
    grade: ColorGrade = ColorGrade.NONE
    overlay_emoji: str | None = None
    overlay_pos: OverlayPosition = OverlayPosition.TOP_RIGHT
    overlay_size: int = Field(default=48, ge=16, le=140)
    pitch: float = Field(default=1.0, ge=0.5, le=2.0)
    # Motion as a real track. Empty list -> fall back to `motion`.
    keyframes: list[Keyframe] = Field(default_factory=list)
    # In/out points on the source media, in seconds from the source's start.
    # They select which part of the source is shown; timeline duration is
    # unchanged, exactly like an NLE's clip in/out handles.
    trim_start: float = Field(default=0.0, ge=0.0, le=600.0)
    trim_end: float = Field(default=0.0, ge=0.0, le=600.0)
    # Play the source backwards (NLE's reverse-speed effect).
    reverse: bool = False
    # Narration gain for this scene (1.0 = unchanged, 0.0 = muted).
    volume: float = Field(default=1.0, ge=0.0, le=2.0)
    # Audio ramps in/out, in seconds — ducked intros, musical outro tails.
    audio_fade_in: float = Field(default=0.0, ge=0.0, le=10.0)
    audio_fade_out: float = Field(default=0.0, ge=0.0, le=10.0)

    # --- the editor's names for the same facts -------------------------------
    # Kept as real fields rather than computed ones so a client can also *send*
    # them: the editor round-trips the scenes it read, and a computed field would
    # be rejected on the way back in.
    index: int = Field(default=0, ge=0)
    duration: float | None = None
    asset_url: str | None = None

    @model_validator(mode="after")
    def _sync_editor_names(self) -> VideoScene:
        """Mirror between the canonical fields and the editor's names, both ways."""
        if self.duration is None:
            self.duration = self.duration_seconds
        else:
            self.duration_seconds = self.duration
        if self.asset_url is None:
            self.asset_url = self.image_url or self.video_url
        elif self.image_url is None and self.video_url is None:
            self.image_url = self.asset_url
        return self


class VideoProject(BaseModel):
    """Editable scene-based video project produced from the script.

    ``background_music_url``/``music_volume`` are the canonical fields;
    ``bgm_asset_url``/``bgm_volume`` are the older names the editor was written
    against and are kept in sync as aliases. ``target_duration_seconds`` is
    derived from the scenes so a client can show planned-vs-actual runtime
    without summing the timeline itself.
    """

    scenes: list[VideoScene] = Field(default_factory=list)
    aspect_ratio: str = "9:16"
    fps: int = Field(default=30, ge=24, le=60)
    captions: bool = True
    background_music: bool = False
    background_music_url: str | None = None
    music_volume: float = Field(default=0.0, ge=0.0, le=1.0)
    voiceover_volume: float = Field(default=1.0, ge=0.0, le=2.0)
    export_quality: str = "high"
    bpm: int = Field(default=120, ge=60, le=180)
    markers: list[TimelineMarker] = Field(default_factory=list)
    # Revision counter, bumped on every saved edit. Lets an external agent
    # (or the UI) detect that someone else moved the timeline underneath it.
    revision: int = Field(default=1, ge=1)
    updated_at: datetime = Field(default_factory=utcnow)
    # --- the editor's names for the same facts (see the class docstring) -----
    target_duration_seconds: float | None = None
    bgm_asset_url: str | None = None
    bgm_volume: float | None = None

    @model_validator(mode="after")
    def _sync_editor_names(self) -> VideoProject:
        """Stamp each scene's position and mirror the editor-side aliases.

        ``index`` is stamped here because a scene cannot know its own position —
        only the list it sits in can. The editor previously assumed the payload
        already carried it.
        """
        for position, scene in enumerate(self.scenes):
            scene.index = position
        if self.bgm_volume is None:
            self.bgm_volume = self.music_volume
        else:
            # ``music_volume`` is the stored, bounded field (0..1): clamp the
            # alias into it rather than letting a client's value fail validation.
            self.music_volume = min(1.0, max(0.0, self.bgm_volume))
        if self.bgm_asset_url is None:
            self.bgm_asset_url = self.background_music_url
        else:
            self.background_music_url = self.bgm_asset_url
        if self.target_duration_seconds is None:
            self.target_duration_seconds = round(
                sum(scene.duration_seconds for scene in self.scenes), 2
            )
        return self


class TimelineStats(BaseModel):
    """Measured properties of a timeline."""

    scene_count: int = 0
    total_seconds: float = 0.0
    narration_seconds: float = 0.0
    transition_seconds: float = 0.0
    marker_count: int = 0
    shortest_scene_seconds: float = 0.0
    longest_scene_seconds: float = 0.0
    average_scene_seconds: float = 0.0
    words: int = 0
    words_per_minute: float = 0.0
    cuts_per_minute: float = 0.0


class TimelineIssue(BaseModel):
    """A single finding from the timeline validator."""

    code: str
    severity: IssueSeverity
    message: str
    hint: str | None = None
    scene_id: str | None = None


class TimelineReport(BaseModel):
    """Validation + measurement report for a video project."""

    stats: TimelineStats
    issues: list[TimelineIssue] = Field(default_factory=list)
    score: int = Field(default=100, ge=0, le=100)
    target_seconds: int | None = None
    generated_at: datetime = Field(default_factory=utcnow)


class SubtitleCue(BaseModel):
    """One caption cue with resolved timing."""

    index: int
    scene_id: str
    start_seconds: float
    end_seconds: float
    text: str


class AudioTrackPlan(BaseModel):
    """How one audio layer is laid down by the renderer."""

    kind: str
    enabled: bool
    volume: float = 1.0
    url: str | None = None
    bpm: int | None = None


class RenderStep(BaseModel):
    """One scene, resolved to an absolute slot on the render timeline."""

    index: int
    scene_id: str
    label: str
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    transition_in: VideoTransition
    transition_seconds: float
    filter: VideoFilter
    effect: SceneEffect
    grade: ColorGrade
    ken_burns: KenBurns
    background: str
    image_url: str | None = None
    text: str = ""
    text_position: TextPosition = TextPosition.CENTER
    text_style: TextStyle = TextStyle.NORMAL
    text_color: str = "#ffffff"
    font_size: int = 48
    entrance: EntranceEffect = EntranceEffect.FADE
    exit: ExitEffect = ExitEffect.NONE
    keyframes: list[Keyframe] = Field(default_factory=list)
    source_in_seconds: float = 0.0
    speed: float = 1.0
    narration_url: str | None = None
    volume: float = 1.0


class RenderPlan(BaseModel):
    """A timeline compiled into an explicit, backend-agnostic render plan.

    This is what a real renderer (ffmpeg today, anything tomorrow) consumes:
    every scene at an absolute time, the caption cues, and the audio layers.
    """

    project_id: str
    aspect_ratio: str
    width: int
    height: int
    fps: int
    total_seconds: float
    steps: list[RenderStep] = Field(default_factory=list)
    subtitles: list[SubtitleCue] = Field(default_factory=list)
    audio: list[AudioTrackPlan] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utcnow)


class RenderRequest(BaseModel):
    export_format: Literal["webm", "mp4"] = "webm"
    audio_ref: str | None = None


class SceneSplitRequest(BaseModel):
    """Payload for splitting a scene at a fraction of its runtime."""

    at: float = Field(default=0.5, gt=0.0, lt=1.0)


class SceneMoveRequest(BaseModel):
    """Payload for reordering a scene on the timeline."""

    to_index: int = Field(ge=0, le=200)


class SceneBulkRequest(BaseModel):
    """Payload for applying one look to many scenes at once."""

    scene_ids: list[str] = Field(min_length=1)
    patch: dict[str, object] = Field(min_length=1)


class MarkerCreate(BaseModel):
    """Payload for adding a timeline marker."""

    time_seconds: float = Field(ge=0.0)
    label: str = ""
    color: str = "#f59e0b"


class SceneSpeedRequest(BaseModel):
    """Payload for retiming a scene."""

    speed: float = Field(ge=0.5, le=2.0)


class SceneReverseRequest(BaseModel):
    """Payload for toggling a scene's reverse playback."""

    reverse: bool = True


class SceneTrimRequest(BaseModel):
    """Payload for setting a scene's source in/out handles."""

    trim_start: float | None = Field(default=None, ge=0.0, le=600.0)
    trim_end: float | None = Field(default=None, ge=0.0, le=600.0)


class SceneAudioRequest(BaseModel):
    """Payload for a scene's audio panel (gain + fades)."""

    volume: float | None = Field(default=None, ge=0.0, le=2.0)
    fade_in: float | None = Field(default=None, ge=0.0, le=10.0)
    fade_out: float | None = Field(default=None, ge=0.0, le=10.0)


class SceneClipResponse(BaseModel):
    """A clipboard holding one copied scene, ready to paste."""

    clip: dict[str, Any]


class ScenePasteRequest(BaseModel):
    """Payload for pasting a copied scene back into the timeline."""

    clip: dict[str, Any]
    after_scene_id: str | None = None


class VideoEditUpdate(BaseModel):
    """Payload for saving a full video project edit."""

    project: VideoProject


class AiAssistRequest(BaseModel):
    """Payload for the AI auto-edit pipeline."""

    fit: bool = True
    beat: bool = False
    bpm: int = Field(default=120, ge=60, le=180)
