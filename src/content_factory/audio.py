"""Automatic music ducking under speech using ffmpeg's sidechain compressor.

The voice track drives a sidechain compressor that lowers the music bed
whenever speech is present, then the two are mixed back together. This keeps
narration intelligible over a musical backing without manual gain automation.

Everything here shells out to ``ffmpeg`` (which is on PATH) and is therefore
fully offline and testable.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass

from .hardware import require_ffmpeg


@dataclass(frozen=True)
class DuckSettings:
    """Tunable parameters for the music-ducking envelope."""

    duck_level_db: float = -12.0
    attack_ms: int = 20
    release_ms: int = 300


def ffmpeg_binary() -> str:
    """Locate the ``ffmpeg`` executable, raising if it is not on PATH."""
    return require_ffmpeg(purpose="music ducking")


def duck_music_under_speech(
    music_path: str,
    voice_path: str,
    out_path: str,
    *,
    duck_level_db: float = -12.0,
    attack_ms: int = 20,
    release_ms: int = 300,
) -> str:
    """Duck ``music_path`` under ``voice_path`` and write the mix to ``out_path``.

    Voice is ffmpeg input 1 and music is input 0. The sidechain compressor
    lowers the music whenever the voice is loud; ``amix`` then blends the
    ducked music with the untouched voice. Returns ``out_path`` on success and
    raises :class:`RuntimeError` if ffmpeg is missing or the command fails.
    """
    binary = ffmpeg_binary()
    command = [
        binary,
        "-y",
        "-i",
        music_path,
        "-i",
        voice_path,
        "-filter_complex",
        (
            "[1:a][0:a]sidechaincompress="
            f"threshold=0.05:ratio=12:attack={attack_ms}:release={release_ms}"
            "[ducked];"
            "[0:a][ducked]amix=inputs=2:duration=first"
        ),
        out_path,
    ]
    proc = subprocess.run(command, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        detail = (proc.stderr or "").strip().splitlines()
        raise RuntimeError(
            f"music ducking failed: {detail[-1] if detail else 'unknown ffmpeg error'}"
        )
    return out_path


def duck_music(
    music_path: str,
    voice_path: str,
    out_path: str,
    settings: DuckSettings | None = None,
) -> str:
    """Thin wrapper around :func:`duck_music_under_speech` using ``DuckSettings``."""
    active = settings or DuckSettings()
    return duck_music_under_speech(
        music_path,
        voice_path,
        out_path,
        duck_level_db=active.duck_level_db,
        attack_ms=active.attack_ms,
        release_ms=active.release_ms,
    )
