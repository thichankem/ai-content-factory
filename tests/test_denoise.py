"""Spectral noise-reduction tests.

Covers the "remove noise" feature:

* ``_spectral_gate`` — FFT-based spectral gating that keeps speech bins and
  suppresses broadband noise (the Audacity/Audition "remove noise" behaviour).
* ``denoise_audio`` — the end-to-end decode → denoise → encode path.
* ``process_voice`` with ``denoise_strength`` (so the enhance chain can denoise).
* The ``audio_denoise`` agent tool (MCP dispatch path).
"""

from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pytest

from content_factory import agent_tools, voice_engine

SR = 44100


def _noisy_signal() -> tuple[np.ndarray, np.ndarray]:
    """A 220 Hz tone buried in broadband noise, plus a pure-noise profile."""
    t = np.linspace(0, 1, SR, endpoint=False)
    rng = np.random.default_rng(0)
    speech = 0.5 * np.sin(2 * np.pi * 220 * t)
    noise = 0.15 * rng.standard_normal(SR)
    mix = (speech + noise).astype(np.float32)
    profile = (0.15 * rng.standard_normal(SR)).astype(np.float32)
    return mix, profile


def _fft_at(samples: np.ndarray, hz: float) -> float:
    spectrum = np.abs(np.fft.rfft(samples))
    freqs = np.fft.rfftfreq(len(samples), 1 / SR)
    idx = int(np.argmin(np.abs(freqs - hz)))
    return float(spectrum[idx])


def test_spectral_gate_preserves_tone_suppresses_noise() -> None:
    mix, profile = _noisy_signal()
    t = np.linspace(0, 1, SR, endpoint=False)
    tone = (0.5 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
    out = voice_engine._spectral_gate(mix, SR, 0.9, profile)
    # The 220 Hz tone survives (~90% of its energy).
    assert _fft_at(out, 220) > 0.8 * _fft_at(mix, 220)
    # The denoised output is much closer to the clean tone than the noisy input
    # was — i.e. the broadband noise is suppressed while the tone is kept.
    err_input = float(np.sqrt(np.mean((mix - tone) ** 2)))
    err_output = float(np.sqrt(np.mean((out - tone) ** 2)))
    assert err_output < 0.75 * err_input
    # No clipping / no reconstruction spikes.
    assert float(np.max(np.abs(out))) <= 1.0


def test_denoise_audio_returns_report_and_decodes() -> None:
    mix, profile = _noisy_signal()
    wav = voice_engine.encode_pcm(mix, SR, "wav")
    profile_wav = voice_engine.encode_pcm(profile, SR, "wav")
    out, report = voice_engine.denoise_audio(
        wav, strength=0.9, noise_profile=profile_wav, export_format="wav"
    )
    assert report["method"] == "spectral_gating"
    assert report["noise_profile"] is True
    assert report["strength"] == 0.9
    assert report["output_peak"] <= 1.0
    # Output decodes to a valid, quieter-but-present signal.
    decoded, sr = voice_engine.decode_to_pcm(out)
    assert sr == SR
    assert decoded.size > 0


def test_denoise_audio_auto_estimates_without_profile() -> None:
    mix, _ = _noisy_signal()
    wav = voice_engine.encode_pcm(mix, SR, "wav")
    out, report = voice_engine.denoise_audio(wav, strength=0.8, export_format="wav")
    assert report["noise_profile"] is False
    decoded, _ = voice_engine.decode_to_pcm(out)
    assert decoded.size > 0


def test_process_voice_with_denoise_strength() -> None:
    mix, profile = _noisy_signal()
    wav = voice_engine.encode_pcm(mix, SR, "wav")
    profile_wav = voice_engine.encode_pcm(profile, SR, "wav")
    out, report = voice_engine.process_voice(
        wav,
        params={"denoise_strength": 0.8},
        noise_profile=profile_wav,
        export_format="wav",
    )
    assert "denoise" in report["steps_applied"]
    assert out


def test_denoise_preset_registered() -> None:
    assert "denoise" in voice_engine.CHAIN_PRESETS
    assert "denoise_strength" in voice_engine.KNOWN_CHAIN_STEPS


def test_agent_audio_denoise(service) -> None:
    fake = {
        "asset_id": "abc",
        "url": "/edited/abc.mp3",
        "method": "spectral_gating",
        "strength": 0.8,
    }
    with patch.object(service, "audio_denoise", return_value=fake) as mock:
        result = agent_tools.dispatch_tool(
            service, "audio_denoise", {"ref": "some-media-id", "strength": 0.8}
        )
    assert result["asset_id"] == "abc"
    mock.assert_called_once_with(
        "some-media-id",
        strength=0.8,
        noise_profile_ref=None,
        format="mp3",
    )


def test_agent_audio_denoise_requires_ref(service) -> None:
    with pytest.raises(agent_tools.ToolError):
        agent_tools.dispatch_tool(service, "audio_denoise", {})
