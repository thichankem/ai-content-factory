from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PlatformProfile:
    key: str
    label: str
    short_form: bool
    title_ideal: tuple[int, int]
    title_hard_max: int
    description_ideal_chars: tuple[int, int]
    description_hard_max: int
    description_ideal_words: int
    keyword_zone: int
    hashtag_ideal: tuple[int, int]
    hashtag_hard_max: int
    tags_ideal: tuple[int, int]
    hook_window: float
    duration_ideal: tuple[float, float]
    duration_hard_max: float
    aspect_required: tuple[str, ...]
    completion_target: float
    avd_ratio_target: float
    ctr_target: float
    cuts_per_minute_min: float
    weights: dict[str, float] = field(default_factory=dict)


YOUTUBE = PlatformProfile(
    key="youtube",
    label="YouTube (long-form)",
    short_form=False,
    title_ideal=(40, 70),
    title_hard_max=100,
    description_ideal_chars=(250, 5000),
    description_hard_max=5000,
    description_ideal_words=250,
    keyword_zone=150,
    hashtag_ideal=(3, 3),
    hashtag_hard_max=60,
    tags_ideal=(8, 15),
    hook_window=30.0,
    duration_ideal=(480.0, 900.0),
    duration_hard_max=43200.0,
    aspect_required=("16:9", "9:16"),
    completion_target=0.40,
    avd_ratio_target=0.45,
    ctr_target=4.0,
    cuts_per_minute_min=6.0,
    weights={
        "search": 0.30,
        "packaging": 0.20,
        "retention": 0.30,
        "distribution": 0.20,
    },
)

SHORTS = PlatformProfile(
    key="youtube_shorts",
    label="YouTube Shorts",
    short_form=True,
    title_ideal=(20, 60),
    title_hard_max=100,
    description_ideal_chars=(80, 1200),
    description_hard_max=5000,
    description_ideal_words=60,
    keyword_zone=60,
    hashtag_ideal=(3, 5),
    hashtag_hard_max=60,
    tags_ideal=(5, 12),
    hook_window=3.0,
    duration_ideal=(15.0, 60.0),
    duration_hard_max=180.0,
    aspect_required=("9:16",),
    completion_target=0.70,
    avd_ratio_target=0.80,
    ctr_target=0.0,
    cuts_per_minute_min=15.0,
    weights={
        "search": 0.20,
        "packaging": 0.30,
        "retention": 0.35,
        "distribution": 0.15,
    },
)

TIKTOK = PlatformProfile(
    key="tiktok",
    label="TikTok",
    short_form=True,
    title_ideal=(0, 0),
    title_hard_max=2200,
    description_ideal_chars=(80, 300),
    description_hard_max=2200,
    description_ideal_words=40,
    keyword_zone=40,
    hashtag_ideal=(3, 5),
    hashtag_hard_max=30,
    tags_ideal=(0, 0),
    hook_window=2.0,
    duration_ideal=(15.0, 34.0),
    duration_hard_max=600.0,
    aspect_required=("9:16",),
    completion_target=0.60,
    avd_ratio_target=0.75,
    ctr_target=0.0,
    cuts_per_minute_min=20.0,
    weights={
        "retention": 0.35,
        "discoverability": 0.30,
        "sound": 0.15,
        "distribution": 0.20,
    },
)

PLATFORM_PROFILES: dict[str, PlatformProfile] = {
    "youtube": YOUTUBE,
    "youtube_shorts": SHORTS,
    "shorts": SHORTS,
    "tiktok": TIKTOK,
}

_DIMENSION_LABELS = {
    "search": "Search match (how findable the metadata makes the video)",
    "discoverability": "Discoverability (caption, on-screen text, spoken keywords)",
    "packaging": "Packaging (thumbnail and title as a click decision)",
    "retention": "Retention structure (hook, pacing, completion)",
    "sound": "Sound (trend fit and beat sync)",
    "distribution": "Distribution (settings, timing, re-watch surface)",
}
