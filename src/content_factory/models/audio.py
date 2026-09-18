"""Audio Lab models: parametric EQ, dynamics and ducking.

Mirrors the contract the studio's Audio Lab screen edits, and matches the
specification in ``docs/SPEC-AUDIO-EDITING.md``. The EQ is the 5-band
parametric set (60 Hz – 12 kHz), and ducking is the Fairlight-style sidechain
(attack/hold/release) — the two behaviours a short-form mixer relies on.
"""

from __future__ import annotations

import enum
from typing import Literal

from pydantic import BaseModel, Field


class EQBandShape(enum.StrEnum):
    """The topology of one parametric EQ band."""

    HIGH_PASS = "high-pass"
    LOW_SHELF = "low-shelf"
    PEAKING = "peaking"
    HIGH_SHELF = "high-shelf"


class ParametricEQBand(BaseModel):
    """One band of a 5-band parametric equaliser."""

    band_id: str
    shape: EQBandShape = EQBandShape.PEAKING
    freq_hz: float = Field(ge=20.0, le=20000.0)
    gain_db: float = Field(default=0.0, ge=-15.0, le=15.0)
    q: float = Field(default=1.41, ge=0.1, le=10.0)


class ParametricEQ(BaseModel):
    """A 5-band parametric equaliser (60 Hz, 250 Hz, 1 kHz, 4 kHz, 12 kHz)."""

    bands: list[ParametricEQBand] = Field(
        default_factory=lambda: [
            ParametricEQBand(band_id="sub", shape=EQBandShape.HIGH_PASS, freq_hz=60.0),
            ParametricEQBand(band_id="low_mid", freq_hz=250.0),
            ParametricEQBand(band_id="mid", freq_hz=1000.0),
            ParametricEQBand(band_id="presence", freq_hz=4000.0),
            ParametricEQBand(band_id="air", shape=EQBandShape.HIGH_SHELF, freq_hz=12000.0),
        ]
    )
    master_gain_db: float = Field(default=0.0, ge=-24.0, le=12.0)


class DynamicsConfig(BaseModel):
    """Downwards compressor / limiter / gate for one track."""

    threshold_db: float = Field(default=-22.0, ge=-60.0, le=0.0)
    ratio: float = Field(default=4.0, ge=1.0, le=20.0)
    knee_db: float = Field(default=4.0, ge=0.0, le=10.0)
    attack_ms: float = Field(default=80.0, ge=1.0, le=500.0)
    release_ms: float = Field(default=450.0, ge=50.0, le=2000.0)
    makeup_gain_db: float = Field(default=0.0, ge=-24.0, le=24.0)


class SidechainDuckingConfig(BaseModel):
    """Fairlight-style sidechain auto-ducking (BGM under voice)."""

    enabled: bool = True
    ducking_depth_db: float = Field(default=-16.0, ge=-36.0, le=0.0)
    threshold_db: float = Field(default=-22.0, ge=-60.0, le=0.0)
    ratio: float = Field(default=4.0, ge=1.0, le=20.0)
    attack_ms: float = Field(default=80.0, ge=1.0, le=500.0)
    release_ms: float = Field(default=450.0, ge=50.0, le=2000.0)
    hold_ms: float = Field(default=100.0, ge=0.0, le=1000.0)


class MultiTrackFaders(BaseModel):
    """Channel-strip faders: narration, BGM, SFX and the master bus."""

    narration_gain: float = Field(default=1.0, ge=0.0, le=2.0)
    narration_mute: bool = False
    bgm_gain: float = Field(default=0.35, ge=0.0, le=2.0)
    bgm_mute: bool = False
    sfx_gain: float = Field(default=0.8, ge=0.0, le=2.0)
    sfx_mute: bool = False
    master_gain: float = Field(default=1.0, ge=0.0, le=2.0)
    target_lufs: float = Field(default=-14.0, ge=-24.0, le=-8.0)


class LoudnessTarget(enum.StrEnum):
    """Broadcast loudness standards (EBU R128 / ITU-R BS.1770-4)."""

    YOUTUBE = "-14.0"
    TIKTOK = "-16.0"
    REELS = "-16.0"
    BROADCAST_EBU = "-23.0"
    BROADCAST_ATSC = "-24.0"


class LoudnessReport(BaseModel):
    """The result of a loudness measurement pass."""

    integrated_lufs: float
    true_peak_dbtp: float
    loudness_range_lu: float
    target: LoudnessTarget
    within_target: bool
    over_peak: bool


class SpectralCleanupConfig(BaseModel):
    """Spectral de-noise / de-hum / de-reverb settings."""

    noise_reduction_db: float = Field(default=12.0, ge=0.0, le=40.0)
    de_hum_hz: Literal[50, 60] = 50
    de_reverb_amount: float = Field(default=0.0, ge=0.0, le=1.0)
    gate_db: float | None = None


class StemIsolationRequest(BaseModel):
    """4-stem separation (vocals, drums, bass, other)."""

    stems: list[Literal["vocals", "drums", "bass", "other"]] = Field(
        default_factory=lambda: ["vocals", "drums", "bass", "other"]
    )


class AudioLabRequest(BaseModel):
    """A full audio-lab pass over one media item."""

    media_id: str
    eq: ParametricEQ | None = None
    dynamics: DynamicsConfig | None = None
    ducking: SidechainDuckingConfig | None = None
    cleanup: SpectralCleanupConfig | None = None
    faders: MultiTrackFaders | None = None
    target_loudness: LoudnessTarget | None = None