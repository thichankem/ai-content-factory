"""Report which optional media/AI tools are available on this machine.

Read-only: it inspects ``PATH`` for binaries and tries to import Python
packages, then prints what each missing tool would unlock. See
``docs/TOOLCHAIN.md`` for installation commands.

Usage::

    python scripts/toolcheck.py            # informational, always exits 0
    python scripts/toolcheck.py --strict   # exit 1 if a required tool is missing
"""

from __future__ import annotations

import argparse
import importlib.util
import pathlib
import shutil
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Tool:
    """One checkable tool and the feature it enables."""

    name: str
    kind: str
    unlocks: str
    required: bool = False
    install_hint: str = ""


TOOLS: tuple[Tool, ...] = (
    Tool(
        name="ffmpeg",
        kind="binary",
        unlocks="real rendering: cut, concat, xfade, overlay, subtitle burn-in, mix",
        required=True,
        install_hint=(
            "winget install Gyan.FFmpeg / brew install ffmpeg / apt install ffmpeg"
        ),
    ),
    Tool(
        name="ffprobe",
        kind="binary",
        unlocks="probing real media duration/resolution before rendering",
        required=True,
        install_hint="ships with ffmpeg",
    ),
    Tool(
        name="yt-dlp",
        kind="binary",
        unlocks="downloading reference videos you have the rights to use",
        install_hint="winget install yt-dlp.yt-dlp | brew install yt-dlp",
    ),
    Tool(
        name="faster_whisper",
        kind="module",
        unlocks="transcription with word timestamps (reference analysis, captions)",
        install_hint="pip install faster-whisper",
    ),
    Tool(
        name="whisperx",
        kind="module",
        unlocks="forced alignment for word-perfect subtitles",
        install_hint="pip install whisperx",
    ),
    Tool(
        name="demucs",
        kind="module",
        unlocks="splitting vocals from music for remixes",
        install_hint="pip install demucs",
    ),
    Tool(
        name="PIL",
        kind="module",
        unlocks="image compositing and thumbnails",
        install_hint="pip install pillow",
    ),
    Tool(
        name="cv2",
        kind="module",
        unlocks="frame analysis, shot detection, stabilization",
        install_hint="pip install opencv-python",
    ),
    Tool(
        name="rembg",
        kind="module",
        unlocks="background removal for subject cut-outs",
        install_hint="pip install rembg",
    ),
    Tool(
        name="moviepy",
        kind="module",
        unlocks="quick programmatic video edits",
        install_hint="pip install moviepy",
    ),
    Tool(
        name="TTS",
        kind="module",
        unlocks="local multilingual voice cloning (Coqui XTTS)",
        install_hint="pip install TTS",
    ),
    Tool(
        name="edge_tts",
        kind="module",
        unlocks="free Microsoft neural voices (primary TTS engine)",
        install_hint="pip install edge-tts",
    ),
    Tool(
        name="gtts",
        kind="module",
        unlocks="dependency-light TTS fallback",
        install_hint="pip install gTTS",
    ),
    Tool(
        name="mutagen",
        kind="module",
        unlocks="measuring audio duration for scene synchronization",
        install_hint="pip install mutagen",
    ),
)


def is_available(tool: Tool) -> bool:
    """Return whether a tool is reachable on this machine."""
    if tool.kind == "binary":
        if shutil.which(tool.name) is not None:
            return True
        exe_ext = ".exe" if sys.platform == "win32" else ""
        candidate = pathlib.Path(sys.executable).parent / f"{tool.name}{exe_ext}"
        return candidate.is_file()
    try:
        return importlib.util.find_spec(tool.name) is not None
    except (ImportError, ValueError):
        return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit non-zero when a required tool is missing",
    )
    args = parser.parse_args(argv)

    present: list[Tool] = []
    missing: list[Tool] = []
    for tool in TOOLS:
        (present if is_available(tool) else missing).append(tool)

    print("AI Content Factory — local tool inventory")
    print("=" * 60)
    for tool in present:
        print(f"  [ok]      {tool.name}")
    for tool in missing:
        flag = "[required]" if tool.required else "[optional]"
        print(f"  [missing] {tool.name} {flag}")
        print(f"            unlocks: {tool.unlocks}")
        if tool.install_hint:
            print(f"            install: {tool.install_hint}")

    print("=" * 60)
    print(f"{len(present)} available, {len(missing)} missing")
    if missing:
        print("See docs/TOOLCHAIN.md for the full install guide.")

    missing_required = [tool for tool in missing if tool.required]
    if args.strict and missing_required:
        print(
            "Strict mode: required tools missing -> "
            + ", ".join(tool.name for tool in missing_required)
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
