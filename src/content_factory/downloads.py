"""Verify that a URL asked for media actually returned media.

A failed extraction used to fall back to fetching the URL raw and storing
whatever came back, so a blocked YouTube request produced a 795 KB HTML page
registered as ``kind=video, mime=video/mp4, duration=null`` — reported as
success. Nothing downstream could use it: ``ffprobe`` found no stream, every
re-encode of the "video" failed, and the palette tools choked on the "image".

The checks live here rather than inside the media library so the rule is in one
place: a payload is media only if its headers say so *and* its bytes (and, when
ffprobe can read it, its streams) agree.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

__all__ = [
    "DownloadRejectedError",
    "looks_like_text_payload",
    "require_media_file",
    "require_media_payload",
]

#: First bytes that give away a web page or an error body rather than media.
TEXT_PAYLOAD_PREFIXES = (
    b"<!doctype",
    b"<html",
    b"<?xml",
    b"<head",
    b'{"',
    b"{\n",
)


class DownloadRejectedError(ValueError):
    """Raised when a URL that was asked for media did not return media."""


def looks_like_text_payload(path: Path) -> bool:
    """Whether a downloaded file starts like a page instead of a container."""
    try:
        with path.open("rb") as handle:
            head = handle.read(512).lstrip().lower()
    except OSError:  # pragma: no cover - an unreadable file is caught elsewhere
        return False
    return head.startswith(TEXT_PAYLOAD_PREFIXES)


def require_media_payload(content_type: Any, url: str) -> None:
    """Refuse a raw download whose Content-Type is not media.

    A server may omit the header entirely; only a *stated* non-media type is
    refused here, because the file itself is checked afterwards anyway.
    """
    if not isinstance(content_type, str):
        return
    kind = content_type.split(";")[0].strip().lower()
    if kind.startswith("text/") or kind in {"application/json", "application/xml"}:
        msg = (
            f"{url} answered with '{kind or 'no content type'}', not audio or "
            "video. The link is not a direct media URL (or the site blocked the "
            "request); use a direct file URL or a supported video link."
        )
        raise DownloadRejectedError(msg)


def require_media_file(path: Path, url: str, *, probe: Any = None) -> None:
    """Refuse a downloaded file that holds no audio or video stream.

    ``probe`` is the probe call to use (defaults to the media library's), so a
    caller that already measured the file does not measure it twice.
    """
    if looks_like_text_payload(path):
        msg = (
            f"{url} returned a web page, not media "
            f"({path.stat().st_size} bytes starting with markup). The extractor "
            "was blocked or the link is not a media URL."
        )
        raise DownloadRejectedError(msg)
    if probe is None:
        from .media import probe_media as probe

    meta = probe(path)
    if meta.get("streams_known") and not (meta["has_video"] or meta["has_audio"]):
        msg = (
            f"{url} downloaded {path.stat().st_size} bytes but ffprobe found no "
            "audio or video stream in them."
        )
        raise DownloadRejectedError(msg)
