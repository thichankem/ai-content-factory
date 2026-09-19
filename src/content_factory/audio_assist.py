"""Accessibility layer for the audio editor.

Like the photo and video layers, this turns every audio operation into plain
language, describes an audio clip from its measurements, and auto-suggests a
mastering chain — so a non-vision user or a text-only AI agent can drive the
whole audio pipeline without hearing a clip.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np

from . import audio_analysis, audio_effects, sfx, voice_engine
from .catalog import detail, grouped_catalog

__all__ = [
    "catalog",
    "describe_audio",
    "describe_operation",
    "suggest_mastering_chain",
]


#: The order categories appear in the catalogue; every one always appears, so a
#: client can render a stable menu even when a category is momentarily empty.
CATEGORY_ORDER = [
    "edit",
    "loudness",
    "mix",
    "rhythm",
    "cleanup",
    "effects",
    "sfx",
    "analysis",
]

#: Plain-language docs for the audio operations surfaced to agents and the UI.
OP_DOCS: dict[str, dict[str, Any]] = {
    "audio_trim": {
        "category": "edit",
        "description": "Trim an audio file to a range.",
        "params": {"start_seconds": "Start.", "end_seconds": "End."},
    },
    "audio_fade": {
        "category": "edit",
        "description": "Apply fade in/out.",
        "params": {"fade_in_seconds": "Fade-in.", "fade_out_seconds": "Fade-out."},
    },
    "audio_loop": {
        "category": "edit",
        "description": "Loop a clip until it reaches a target duration.",
        "params": {"duration_seconds": "Target length."},
    },
    "audio_retime": {
        "category": "edit",
        "description": "Change tempo without changing pitch.",
        "params": {"factor": "Speed factor."},
    },
    "audio_normalize": {
        "category": "loudness",
        "description": "Loudness-normalise to a streaming target (EBU R128).",
        "params": {"target_lufs": "Target loudness."},
    },
    "audio_mix": {
        "category": "mix",
        "description": "Mix several tracks with per-track gain, delay, looping "
        "and optional voice-ducking.",
        "params": {"tracks": "List of {path, gain_db, offset_seconds, role}."},
    },
    "duck_music": {
        "category": "mix",
        "description": "Duck a music bed under a voice track.",
        "params": {"duck_db": "How much to duck."},
    },
    "music_beat_grid": {
        "category": "rhythm",
        "description": "Detect tempo and beat timestamps.",
        "params": {"bpm": "Optional known tempo."},
    },
    "enhance_voice": {
        "category": "cleanup",
        "description": "Enhance a voice track (denoise, eq, compression).",
        "params": {"preset": "Named chain."},
    },
    "audio_denoise": {
        "category": "cleanup",
        "description": "Remove background noise via spectral gating.",
        "params": {"strength": "0..1."},
    },
    "apply_audio_effect": {
        "category": "effects",
        "description": "Apply any DSP effect (equalizer, reverb, voice changer, "
        "creative effects) to audio.",
        "params": {"name": "Effect name.", "params": "Effect parameters."},
    },
    "synthesize_sfx": {
        "category": "sfx",
        "description": "Generate a sound effect from scratch (whoosh, impact, "
        "explosion, footstep, ambience, transition, ui_click).",
        "params": {"name": "SFX name.", "duration": "Length in seconds."},
    },
    "analyze_audio": {
        "category": "analysis",
        "description": "Measure an audio clip: waveform, spectrogram, frequency "
        "spectrum, RMS, dynamic range, clipping, noise floor, phase correlation.",
        "params": {},
    },
}


def catalog() -> dict[str, Any]:
    """Every audio operation grouped by category, with descriptions.

    The hand-written operations are folded together with the DSP effects and
    the synthesised SFX, which is why the entries are prefixed
    (``effect_*`` / ``sfx_*``) rather than folded into ``OP_DOCS``: the prefix
    is what lets :func:`describe_operation` route a name back to its engine.
    """
    docs: dict[str, dict[str, Any]] = dict(OP_DOCS)
    for effect in audio_effects.audio_effect_catalog()["effects"]:
        docs[f"effect_{effect['name']}"] = {
            "category": "effects",
            "description": effect["description"],
            "params": effect["params"],
        }
    for sound in sfx.sfx_catalog()["sfx"]:
        docs[f"sfx_{sound['name']}"] = {
            "category": "sfx",
            "description": sound["description"],
            "params": {},
        }
    return grouped_catalog(docs, CATEGORY_ORDER)


def describe_operation(name: str) -> dict[str, Any]:
    """Explain one audio operation in plain language."""
    name = name.lower()
    doc: Mapping[str, Any] | None = OP_DOCS.get(name)
    if doc is None and name.startswith("effect_"):
        doc = _effect_doc(name[len("effect_") :])
        if doc is None:
            raise ValueError(f"Unknown audio effect '{name[len('effect_') :]}'.")
    if doc is None and name.startswith("sfx_"):
        doc = _sfx_doc(name[len("sfx_") :])
        if doc is None:
            raise ValueError(f"Unknown SFX '{name[len('sfx_') :]}'.")
    if doc is None:
        raise ValueError(f"Unknown audio operation '{name}'.")
    return detail(name, doc)


def _effect_doc(name: str) -> dict[str, Any] | None:
    """The catalogue document for one DSP effect, by its short name."""
    for effect in audio_effects.audio_effect_catalog()["effects"]:
        if effect["name"] == name:
            return {
                "category": "effects",
                "description": effect["description"],
                "params": effect["params"],
            }
    return None


def _sfx_doc(name: str) -> dict[str, Any] | None:
    """The catalogue document for one synthesised sound effect."""
    for sound in sfx.sfx_catalog()["sfx"]:
        if sound["name"] == name:
            return {
                "category": "sfx",
                "description": sound["description"],
                "params": {},
            }
    return None


def describe_effect(name: str) -> dict[str, Any]:
    """Describe a DSP effect by its short name."""
    doc = _effect_doc(name)
    if doc is None:
        raise ValueError(f"Unknown audio effect '{name}'.")
    return detail(f"effect_{name}", doc)


def describe_sfx(name: str) -> dict[str, Any]:
    """Describe a synthesised sound effect by its short name."""
    doc = _sfx_doc(name)
    if doc is None:
        raise ValueError(f"Unknown SFX '{name}'.")
    return detail(f"sfx_{name}", doc)


def describe_audio(samples: np.ndarray, sr: int = 44100) -> dict[str, Any]:
    """Turn audio measurements into a plain-language description."""
    analysis = audio_analysis.analyze_samples(samples, sr)
    dyn = analysis["dynamic_range"]
    clip = analysis["clipping"]
    freq = analysis["frequency"]
    noise = analysis["noise_floor"]

    if clip["clipping"]:
        loudness = "loud with possible clipping"
    elif dyn["crest_factor_db"] > 18:
        loudness = "wide dynamic range (peaky)"
    elif dyn["crest_factor_db"] < 8:
        loudness = "compressed / dense"
    else:
        loudness = "balanced"

    dominant = freq["dominant_freq_hz"]
    if dominant < 200:
        timbre = "bass-heavy"
    elif dominant < 2000:
        timbre = "mid-focused"
    else:
        timbre = "bright / treble-heavy"

    snr = noise.get("signal_to_noise_db")
    if snr is not None and snr < 15:
        cleanliness = "noisy (low signal-to-noise)"
    elif snr is not None and snr < 30:
        cleanliness = "somewhat noisy"
    else:
        cleanliness = "clean"

    summary = (
        f"This audio is {loudness}, {timbre}, and {cleanliness}. The dominant "
        f"frequency is about {dominant:.0f} Hz."
    )
    return {
        "summary": summary,
        "details": {
            "loudness": loudness,
            "timbre": timbre,
            "cleanliness": cleanliness,
            "dominant_freq_hz": round(dominant, 1),
            "crest_factor_db": dyn["crest_factor_db"],
            "clipping": clip["clipping"],
            "signal_to_noise_db": snr,
        },
        "analysis": analysis,
    }


def suggest_mastering_chain(samples: np.ndarray, sr: int = 44100) -> dict[str, Any]:
    """Auto-suggest a mastering chain from the audio measurements."""
    analysis = audio_analysis.analyze_samples(samples, sr)
    suggestions: list[dict[str, Any]] = []

    if analysis["clipping"]["clipping"]:
        suggestions.append(
            {
                "op": "apply_audio_effect",
                "params": {"name": "limiter", "params": {"ceiling_db": -1.0}},
                "reason": "The audio is clipping; add a limiter to protect the "
                "ceiling.",
            }
        )
    noise = analysis["noise_floor"]
    if noise.get("signal_to_noise_db") is not None and noise["signal_to_noise_db"] < 15:
        suggestions.append(
            {
                "op": "audio_denoise",
                "params": {"strength": 0.6},
                "reason": "Low signal-to-noise; reduce background noise.",
            }
        )
    freq = analysis["frequency"]
    bands = {b["name"]: b["energy"] for b in freq["bands"]}
    if bands.get("20-60Hz", 0) > bands.get("250-500Hz", 1) * 2:
        suggestions.append(
            {
                "op": "apply_audio_effect",
                "params": {"name": "highpass", "params": {"freq": 80.0}},
                "reason": "Strong low rumble; high-pass to clean the sub-bass.",
            }
        )
    if analysis["dynamic_range"]["crest_factor_db"] > 18:
        suggestions.append(
            {
                "op": "apply_audio_effect",
                "params": {
                    "name": "compressor",
                    "params": {"threshold_db": -18.0, "ratio": 3.0},
                },
                "reason": "Wide dynamic range; compress to even the level.",
            }
        )
    # Always suggest a final loudness-normalise.
    suggestions.append(
        {
            "op": "audio_normalize",
            "params": {"target_lufs": -14.0},
            "reason": "Normalise to a streaming loudness target.",
        }
    )
    return {
        "suggestions": suggestions,
        "count": len(suggestions),
        "summary": "Suggested mastering chain based on the audio measurements.",
    }


def execute_mastering_chain(
    samples: np.ndarray, sr: int = 44100
) -> tuple[np.ndarray, dict[str, Any]]:
    """Run the auto-suggested mastering chain on PCM and return the result.

    Executes each suggestion in order (denoise → effects → loudness normalise)
    purely with numpy DSP, so a non-vision agent can produce a mastered file
    without hearing it first.
    """
    chain = suggest_mastering_chain(samples, sr)
    applied: list[str] = []
    out = np.asarray(samples, dtype=np.float32)
    for step in chain["suggestions"]:
        op = step["op"]
        params = step.get("params") or {}
        if op == "audio_denoise":
            out = voice_engine.denoise_pcm(
                out, sr, strength=float(params.get("strength", 0.6))
            )
            applied.append("denoise")
        elif op == "apply_audio_effect":
            name = params.get("name")
            if name:
                out = audio_effects.apply_audio_effect(
                    out, sr, name, params.get("params")
                )
                applied.append(f"effect:{name}")
        elif op == "audio_normalize":
            out = voice_engine.normalize_loudness_pcm(
                out, float(params.get("target_lufs", -14.0))
            )
            applied.append("normalize")
    out = np.asarray(out, dtype=np.float32)
    report = {
        "steps": applied,
        "count": len(applied),
        "peak": round(float(np.max(np.abs(out))) if out.size else 0.0, 4),
        "rms": round(float(np.sqrt(np.mean(out**2))) if out.size else 0.0, 4),
    }
    return out, report
