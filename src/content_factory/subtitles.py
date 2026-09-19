"""WebVTT caption parsing — text and cue timings.

Captions are the *instant* transcript path: YouTube already knows the words and
the timecodes, so the only work left is reading the file. That parsing is pure
text handling with nothing to do with the media library, so it lives here and
can be tested (and reused) without constructing one.

``vtt_to_segments`` exists because the timings were being thrown away: a
transcript returned the full ``text`` next to ``segments: []``, which made the
tool look like it had found timecodes it had actually discarded — and a caller
that trusted them for subtitle burn-in or beat-aligned cuts had nothing to use.
"""

from __future__ import annotations

import re

__all__ = ["parse_timestamp", "vtt_to_segments", "vtt_to_text"]


def parse_timestamp(value: str) -> float | None:
    """``00:01:02.500`` (or ``01:02.500``) as seconds, or ``None``.

    WebVTT may use a comma as the decimal separator (``00:00:01,500``), which is
    what SubRip writes, so both are accepted.
    """
    parts = value.strip().split(":")
    if not 2 <= len(parts) <= 3:
        return None
    try:
        numbers = [float(part.replace(",", ".")) for part in parts]
    except ValueError:
        return None
    seconds = 0.0
    for number in numbers:
        seconds = seconds * 60 + number
    return round(seconds, 3)


def vtt_to_segments(vtt: str) -> list[dict[str, float | str]]:
    """Parse a WebVTT file into ``{"start_seconds", "end_seconds", "text"}``."""
    segments: list[dict[str, float | str]] = []
    start: float | None = None
    end: float | None = None
    lines: list[str] = []

    def flush() -> None:
        text = " ".join(lines).strip()
        if start is not None and end is not None and text:
            segments.append({"start_seconds": start, "end_seconds": end, "text": text})

    for raw in vtt.splitlines():
        line = raw.strip()
        if "-->" in line:
            flush()
            left, _, right = line.partition("-->")
            start = parse_timestamp(left.split()[-1] if left.split() else "")
            right_tokens = right.split()
            end = parse_timestamp(right_tokens[0]) if right_tokens else None
            lines = []
            continue
        if not line or line.startswith(("WEBVTT", "Kind:", "Language:", "NOTE")):
            continue
        cleaned = re.sub(r"<[^>]+>", "", line)
        if cleaned:
            lines.append(cleaned)
    flush()
    return segments


def vtt_to_text(vtt: str) -> str:
    """Strip a WebVTT file down to its spoken lines, timings and all."""
    lines: list[str] = []
    for raw in vtt.splitlines():
        line = raw.strip()
        if not line or line.startswith("WEBVTT") or "-->" in line:
            continue
        if line.startswith(("Kind:", "Language:", "NOTE")):
            continue
        line = re.sub(r"<[^>]+>", "", line)
        if line:
            lines.append(line)
    return " ".join(lines).strip()
