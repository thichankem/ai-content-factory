"""Regression guards for ``media_probe``'s ffmpeg-only probing fallback.

``imageio-ffmpeg`` ships ``ffmpeg`` but not ``ffprobe``, so a machine can have a
working ffmpeg and no prober. The media tools used to refuse to read anything in
that case; they now parse ffmpeg's own metadata instead. These tests pin the
parser without needing either binary installed.
"""

from __future__ import annotations

import pathlib
import types

from content_factory import media_probe

#: Real ``ffmpeg -i`` output for a 4 s 640x360 h264/aac clip, trimmed to the
#: lines the parser reads. Split into pieces so no source line breaks E501.
_VIDEO_LINE = (
    "  Stream #0:0[0x1](und): Video: h264 (High) (avc1 / 0x31637661), "
    "yuv420p, 640x360 [SAR 1:1 DAR 16:9], 25 fps, 25 tbr, 12800 tbn (default)\n"
)
_AUDIO_LINE = (
    "  Stream #0:1[0x2](und): Audio: aac (LC) (mp4a / 0x6134706D), "
    "44100 Hz, mono, fltp, 69 kb/s (default)\n"
)
_FFMPEG_STDERR = (
    "ffmpeg version 7.1-essentials_build Copyright (c) 2000-2024\n"
    "Input #0, mov,mp4,m4a,3gp,3g2,mj2, from 'clip.mp4':\n"
    "  Metadata:\n"
    "    encoder         : Lavf61.7.100\n"
    "  Duration: 00:00:04.00, start: 0.000000, bitrate: 123 kb/s\n"
    + _VIDEO_LINE
    + _AUDIO_LINE
    + "At least one output file must be specified\n"
).encode()


def _patched(monkeypatch) -> dict:
    monkeypatch.setattr(media_probe, "_binary", lambda name: f"/fake/{name}")
    monkeypatch.setattr(
        media_probe.subprocess,
        "run",
        lambda *a, **k: types.SimpleNamespace(stderr=_FFMPEG_STDERR, returncode=1),
    )
    return media_probe._probe_json_from_ffmpeg(pathlib.Path("clip.mp4"))


def test_ffmpeg_fallback_reads_container_and_duration(monkeypatch) -> None:
    data = _patched(monkeypatch)
    assert data["format"]["format_name"] == "mov,mp4,m4a,3gp,3g2,mj2"
    assert data["format"]["duration"] == 4.0
    assert data["format"]["bit_rate"] == 123000


def test_ffmpeg_fallback_reads_video_and_audio_streams(monkeypatch) -> None:
    data = _patched(monkeypatch)
    video = next(s for s in data["streams"] if s["codec_type"] == "video")
    audio = next(s for s in data["streams"] if s["codec_type"] == "audio")
    assert (video["codec_name"], video["width"], video["height"]) == ("h264", 640, 360)
    assert video["avg_frame_rate"] == "25/1"
    assert audio["codec_name"] == "aac"
    assert audio["sample_rate"] == "44100"
    assert audio["channels"] == 1


def test_probe_reads_the_fallback_shape(monkeypatch, tmp_path) -> None:
    """``probe`` must digest the fallback exactly as it does ffprobe's JSON."""
    clip = tmp_path / "clip.mp4"
    clip.write_bytes(b"\x00")
    monkeypatch.setattr(media_probe, "_binary", lambda name: f"/fake/{name}")
    monkeypatch.setattr(media_probe, "resolve_ffprobe", lambda *a, **k: None)
    monkeypatch.setattr(
        media_probe.subprocess,
        "run",
        lambda *a, **k: types.SimpleNamespace(stderr=_FFMPEG_STDERR, returncode=1),
    )
    info = media_probe.probe(clip)
    assert info["has_video"] is True
    assert info["has_audio"] is True
    assert info["width"] == 640 and info["height"] == 360
    assert info["fps"] == 25.0
    assert info["duration_seconds"] == 4.0
    assert info["sample_rate"] == 44100
    assert info["channels"] == 1
