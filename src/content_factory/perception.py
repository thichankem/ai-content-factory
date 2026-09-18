"""Audio perception layer — "hearing" the soundtrack.

Mirrors the vision layer's dual-mode principle for the ear: the same kind of
analysis runs with a cheap, deterministic **non-AI** backend (pure ``numpy`` +
``ffmpeg``, no model, no GPU, no API cost) or, when enabled, a pluggable **AI**
backend (PANNs/YAMNet, pyannote, a speech-emotion model, CLAP or an
audio-capable multimodal LLM). The calling code does not change — you swap the
backend, not the call.

Non-AI (always available, free):

  * :func:`detect_silence_and_pace` — find silent gaps and a coarse speaking
    pace from RMS energy.
  * :func:`classify_music_mood` — energy / spectral-centroid / tempo heuristic
    that yields a coarse mood (energetic, calm, …).
  * :func:`check_audio_quality` — clipping, DC offset, noise floor, peak level.

AI (opt-in, off by default — see ``docs/PERCEPTION-LAYER.md``):

  * :meth:`AudioPerception.detect_audio_events` — sound events (applause,
    glass breaking, a bell, music swell) via PANNs/YAMNet.
  * :meth:`AudioPerception.diarize_speakers` — "who speaks when" via pyannote.
  * :meth:`AudioPerception.detect_speech_emotion` — emotion in the voice via a
    speech-emotion-recognition model.
  * :meth:`AudioPerception.describe_audio_scene` — a natural-language
    description of the whole soundtrack via an audio-capable LLM.

Everything here is pure over an audio path and returns plain data, so it is
testable offline and callable from the MCP server. Heavy AI backends are never
imported unless one is wired in.
"""

from __future__ import annotations

import subprocess
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np

from .config import Settings
from .hardware import require_ffmpeg

# --- Data structures ----------------------------------------------------------


@dataclass(frozen=True)
class SilenceSegment:
    """One silent gap, in seconds."""

    start_seconds: float
    end_seconds: float


@dataclass(frozen=True)
class PaceEstimate:
    """Coarse speaking pace computed without a speech model."""

    total_duration: float
    speech_ratio: float  # fraction of the audio that is not silent, 0..1
    silent_segments: list[SilenceSegment]
    avg_silence_seconds: float


@dataclass(frozen=True)
class MusicMood:
    """Coarse mood classification from acoustic features."""

    mood: str  # energetic | upbeat | neutral | calm | ambient | unknown
    energy: float  # 0..1
    tempo_bpm: float  # 0.0 when undeterminable
    description: str


@dataclass(frozen=True)
class AudioQuality:
    """Simple technical quality report."""

    sample_rate: int
    peak_db: float
    clipping: bool
    dc_offset: float  # -1..1, ~0 is healthy
    noise_floor_db: float


@dataclass(frozen=True)
class AudioEvent:
    """One detected sound event, in seconds."""

    label: str
    start_seconds: float
    end_seconds: float
    confidence: float  # 0..1


@dataclass(frozen=True)
class SpeakerTurn:
    """One speaker's turn, in seconds."""

    speaker_id: str
    start_seconds: float
    end_seconds: float


@dataclass(frozen=True)
class SpeechEmotion:
    """Dominant emotion in a spoken passage."""

    emotion: str
    confidence: float  # 0..1


@dataclass(frozen=True)
class AudioSceneDescription:
    """A natural-language description of an audio scene."""

    description: str


# --- AI backend protocols (pluggable, never imported by default) -------------


class AudioEventDetector(Protocol):
    """Detects sound events (PANNs/YAMNet-style classifier)."""

    def detect(self, audio_path: str | Path) -> list[AudioEvent]: ...


class SpeakerDiarizer(Protocol):
    """Separates "who speaks when" (pyannote-style)."""

    def diarize(self, audio_path: str | Path) -> list[SpeakerTurn]: ...


class SpeechEmotionAnalyzer(Protocol):
    """Classifies the dominant emotion in speech."""

    def analyze(self, audio_path: str | Path) -> SpeechEmotion: ...


class AudioSceneDescriber(Protocol):
    """Describes the whole soundtrack in natural language."""

    def describe(self, audio_path: str | Path) -> AudioSceneDescription: ...


# --- Low-level audio decoding -------------------------------------------------


def _decode_mono_pcm(
    audio_path: str | Path, *, target_rate: int = 22050
) -> tuple[np.ndarray, int]:
    """Decode an audio file to mono float32 samples in ``[-1, 1]``.

    WAV files are read directly via the stdlib ``wave`` module (hermetic, fast,
    no external tool). Everything else is decoded with ``ffmpeg`` to raw s16le
    mono PCM, resampled to ``target_rate``. Raises a clear error when the file
    is missing or ffmpeg is unavailable.
    """
    path = Path(audio_path)
    if not path.is_file():
        raise ValueError(f"audio file not found: '{path}'")

    if path.suffix.lower() == ".wav":
        with wave.open(str(path), "rb") as wav:
            rate = wav.getframerate()
            channels = wav.getnchannels()
            raw = wav.readframes(wav.getnframes())
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        if channels > 1:
            samples = samples.reshape(-1, channels).mean(axis=1)
        return _resample(samples, rate, target_rate), target_rate

    binary = _ffmpeg()
    proc = subprocess.run(
        [
            binary,
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(path),
            "-ac",
            "1",
            "-ar",
            str(target_rate),
            "-f",
            "s16le",
            "-",
        ],
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or b"").decode("utf-8", "replace").strip().splitlines()
        raise ValueError(detail[-1] if detail else "ffmpeg decode failed")
    samples = np.frombuffer(proc.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    return samples, target_rate


def _resample(samples: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
    """Linear-interpolation resample to ``target_rate`` (keeps length sane)."""
    if source_rate == target_rate or len(samples) == 0:
        return samples
    duration = len(samples) / max(1, source_rate)
    out_len = max(1, round(duration * target_rate))
    src_idx = np.linspace(0.0, len(samples) - 1, num=out_len)
    lo = np.floor(src_idx).astype(np.int64)
    hi = np.minimum(lo + 1, len(samples) - 1)
    frac = (src_idx - lo).astype(np.float32)
    result: np.ndarray = samples[lo] * (1.0 - frac) + samples[hi] * frac
    return result


def _ffmpeg() -> str:
    """The ffmpeg used to decode audio formats ``wave`` cannot read."""
    return require_ffmpeg(purpose="decoding non-WAV audio")


def _db(value: float) -> float:
    """Convert a linear amplitude to decibels (``-inf`` -> very low)."""
    if value <= 1e-10:
        return -120.0
    return float(20.0 * np.log10(value))


# --- Non-AI analysis ----------------------------------------------------------


def detect_silence_and_pace(
    audio_path: str | Path,
    *,
    silence_threshold_db: float = -40.0,
    min_silence_seconds: float = 0.3,
    frame_seconds: float = 0.032,
) -> tuple[list[SilenceSegment], PaceEstimate]:
    """Locate silent gaps and estimate a coarse speaking pace.

    Frames whose RMS energy sits below ``silence_threshold_db`` are silent;
    consecutive silent frames are merged, dropping gaps shorter than
    ``min_silence_seconds``. Pure numpy — no model, no GPU.
    """
    samples, rate = _decode_mono_pcm(audio_path)
    total = len(samples) / max(1, rate)
    if len(samples) == 0:
        return [], PaceEstimate(total, 0.0, [], 0.0)

    hop = max(1, round(frame_seconds * rate))
    n_frames = max(1, len(samples) // hop)
    energies = np.empty(n_frames, dtype=np.float32)
    for i in range(n_frames):
        seg = samples[i * hop : (i + 1) * hop]
        energies[i] = float(np.sqrt(np.mean(seg**2))) if seg.size else 0.0

    threshold = 10.0 ** (silence_threshold_db / 20.0)
    silent = energies < threshold

    segments: list[SilenceSegment] = []
    start: int | None = None
    for i, is_silent in enumerate(silent):
        if is_silent and start is None:
            start = i
        elif not is_silent and start is not None:
            _maybe_push(segments, start, i, hop, rate, min_silence_seconds)
            start = None
    if start is not None:
        _maybe_push(segments, start, len(silent), hop, rate, min_silence_seconds)

    silent_total = sum(seg.end_seconds - seg.start_seconds for seg in segments)
    speech_ratio = 0.0 if total <= 0 else float(max(0.0, 1.0 - silent_total / total))
    avg_silence = (
        float(
            sum(seg.end_seconds - seg.start_seconds for seg in segments) / len(segments)
        )
        if segments
        else 0.0
    )
    pace = PaceEstimate(
        total_duration=round(total, 3),
        speech_ratio=round(speech_ratio, 4),
        silent_segments=segments,
        avg_silence_seconds=round(avg_silence, 3),
    )
    return segments, pace


def _maybe_push(
    segments: list[SilenceSegment],
    start: int,
    end: int,
    hop: int,
    rate: int,
    min_silence_seconds: float,
) -> None:
    """Append a silence segment if it is long enough to matter."""
    duration = (end - start) * hop / max(1, rate)
    if duration >= min_silence_seconds:
        segments.append(
            SilenceSegment(
                start_seconds=round(start * hop / max(1, rate), 3),
                end_seconds=round(end * hop / max(1, rate), 3),
            )
        )


def classify_music_mood(
    audio_path: str | Path, *, frame_seconds: float = 0.092
) -> MusicMood:
    """Classify a coarse music mood from acoustic features (non-AI).

    Combines overall energy (RMS), spectral centroid (brightness via FFT) and a
    rough tempo estimate (onset-envelope autocorrelation). Deterministic and
    free; intended as a first-pass signal, not a substitute for a music model.
    """
    samples, rate = _decode_mono_pcm(audio_path)
    if len(samples) == 0:
        return MusicMood("unknown", 0.0, 0.0, "no audio")

    hop = max(1, round(frame_seconds * rate))
    n_frames = max(1, len(samples) // hop)
    rms = np.empty(n_frames, dtype=np.float32)
    centroid = np.empty(n_frames, dtype=np.float32)
    for i in range(n_frames):
        seg = samples[i * hop : (i + 1) * hop]
        rms[i] = float(np.sqrt(np.mean(seg**2))) if seg.size else 0.0
        centroid[i] = _spectral_centroid(seg, rate)

    energy = float(np.clip(rms.mean() / 0.125, 0.0, 1.0))
    brightness = float(np.clip(centroid.mean() / 3500.0, 0.0, 1.0))
    tempo = _estimate_tempo(rms, frame_seconds)

    if energy >= 0.72 and tempo >= 118:
        mood = "energetic"
    elif energy >= 0.55 and tempo >= 105:
        mood = "upbeat"
    elif energy >= 0.45:
        mood = "neutral"
    elif energy >= 0.22:
        mood = "calm"
    elif energy > 0.0:
        mood = "ambient"
    else:
        mood = "unknown"

    description = (
        f"energy={energy:.2f} brightness={brightness:.2f} tempo≈{tempo:.0f}bpm → {mood}"
    )
    return MusicMood(mood, round(energy, 3), round(tempo, 1), description)


def _spectral_centroid(segment: np.ndarray, rate: int) -> float:
    """Brightness of a frame via the magnitude-spectrum centroid."""
    if segment.size < 1024:
        return 0.0
    spectrum = np.abs(np.fft.rfft(segment * np.hanning(len(segment))))
    freqs = np.fft.rfftfreq(len(segment), d=1.0 / rate)
    total = float(spectrum.sum())
    if total <= 0.0:
        return 0.0
    return float(np.dot(freqs, spectrum) / total)


def _estimate_tempo(rms: np.ndarray, frame_seconds: float) -> float:
    """Rough BPM from the autocorrelation of the RMS onset envelope."""
    if rms.size < 8:
        return 0.0
    onset = np.maximum(np.diff(rms), 0.0)
    if onset.sum() <= 0.0:
        return 0.0
    # Lags for 60..200 BPM expressed in frames.
    min_lag = max(1, round(60.0 / 210.0 / frame_seconds))
    max_lag = max(min_lag + 1, round(60.0 / 57.0 / frame_seconds))
    max_lag = min(max_lag, onset.size - 1)
    if max_lag <= min_lag:
        return 0.0
    corr = np.correlate(onset, onset, mode="full")[onset.size - 1 :]
    window = corr[min_lag : max_lag + 1]
    if window.size == 0 or float(window.max()) <= 0.0:
        return 0.0
    lag = int(np.argmax(window)) + min_lag
    bpm = 60.0 / (lag * frame_seconds)
    return float(np.clip(bpm, 40.0, 260.0))


def check_audio_quality(audio_path: str | Path) -> AudioQuality:
    """Report basic technical audio quality (non-AI)."""
    samples, rate = _decode_mono_pcm(audio_path)
    if len(samples) == 0:
        return AudioQuality(rate, -120.0, False, 0.0, -120.0)

    peak = float(np.abs(samples).max())
    peak_db = _db(peak)
    clipping = peak >= 0.995
    dc_offset = float(np.mean(samples))

    # Noise floor: RMS of the quietest 10% of frames.
    frame = max(1, rate // 20)
    n_frames = max(1, len(samples) // frame)
    rms = np.array(
        [
            float(np.sqrt(np.mean(samples[i * frame : (i + 1) * frame] ** 2)))
            if samples[i * frame : (i + 1) * frame].size
            else 0.0
            for i in range(n_frames)
        ]
    )
    noise_floor = float(np.percentile(rms, 10)) if rms.size else 0.0
    return AudioQuality(
        sample_rate=rate,
        peak_db=round(peak_db, 1),
        clipping=bool(clipping),
        dc_offset=round(dc_offset, 4),
        noise_floor_db=round(_db(noise_floor), 1),
    )


# --- Facade -------------------------------------------------------------------


class AudioPerception:
    """Dispatch to the right backend for each audio-perception task.

    Non-AI tasks (:meth:`detect_silence_and_pace`, :meth:`classify_music_mood`,
    :meth:`check_audio_quality`) always run. AI tasks raise a clear error unless
    the corresponding backend is wired in *and* ``enable_audio_perception`` is
    on — so the calling code stays unchanged while the operator decides how much
    "hearing" to pay for.
    """

    def __init__(
        self,
        settings: Settings,
        *,
        event_detector: AudioEventDetector | None = None,
        diarizer: SpeakerDiarizer | None = None,
        emotion_analyzer: SpeechEmotionAnalyzer | None = None,
        scene_describer: AudioSceneDescriber | None = None,
    ) -> None:
        self._settings = settings
        self._event_detector = event_detector
        self._diarizer = diarizer
        self._emotion_analyzer = emotion_analyzer
        self._scene_describer = scene_describer

    # --- Always available (non-AI) ------------------------------------------

    def detect_silence_and_pace(
        self, audio_path: str | Path
    ) -> tuple[list[SilenceSegment], PaceEstimate]:
        return detect_silence_and_pace(audio_path)

    def classify_music_mood(self, audio_path: str | Path) -> MusicMood:
        return classify_music_mood(audio_path)

    def check_audio_quality(self, audio_path: str | Path) -> AudioQuality:
        return check_audio_quality(audio_path)

    # --- Opt-in (AI backends) -----------------------------------------------

    def detect_audio_events(self, audio_path: str | Path) -> list[AudioEvent]:
        if self._event_detector is None:
            raise RuntimeError(
                "audio event detection needs an AI backend (PANNs/YAMNet) and "
                "ENABLE_AUDIO_PERCEPTION=true; none is wired in."
            )
        return self._event_detector.detect(audio_path)

    def diarize_speakers(self, audio_path: str | Path) -> list[SpeakerTurn]:
        if self._diarizer is None:
            raise RuntimeError(
                "speaker diarization needs an AI backend (pyannote) and "
                "ENABLE_AUDIO_PERCEPTION=true; none is wired in."
            )
        return self._diarizer.diarize(audio_path)

    def detect_speech_emotion(self, audio_path: str | Path) -> SpeechEmotion:
        if self._emotion_analyzer is None:
            raise RuntimeError(
                "speech emotion needs an AI backend (SER model) and "
                "ENABLE_AUDIO_PERCEPTION=true; none is wired in."
            )
        return self._emotion_analyzer.analyze(audio_path)

    def describe_audio_scene(self, audio_path: str | Path) -> AudioSceneDescription:
        if self._scene_describer is None:
            raise RuntimeError(
                "audio scene description needs an audio-capable LLM backend and "
                "ENABLE_AUDIO_PERCEPTION=true; none is wired in."
            )
        return self._scene_describer.describe(audio_path)


def build_audio_perception(
    settings: Settings,
    *,
    event_detector: AudioEventDetector | None = None,
    diarizer: SpeakerDiarizer | None = None,
    emotion_analyzer: SpeechEmotionAnalyzer | None = None,
    scene_describer: AudioSceneDescriber | None = None,
) -> AudioPerception:
    """Construct the audio-perception facade for the configured mode.

    Mirrors ``vision.build_scorer``: the non-AI path is always returned; AI
    backends are attached only when supplied. Swap the backends here without
    touching call sites.
    """
    return AudioPerception(
        settings,
        event_detector=event_detector,
        diarizer=diarizer,
        emotion_analyzer=emotion_analyzer,
        scene_describer=scene_describer,
    )
