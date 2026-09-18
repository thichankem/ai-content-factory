"""Rule-based QA / critique layer for the AI Content Factory.

This module is the *critic*, deliberately separated from content creation. It
answers three questions about a finished or in-progress asset, purely over
plain data and file paths, so it is testable offline and callable from the MCP
server:

  * :func:`check_platform` — does the asset fit a target platform's hard limits
    (duration, aspect ratio) and soft expectations (word count, forbidden
    phrases)?
  * :func:`check_brand` — does the asset respect a brand kit (palette, fonts,
    logo presence)?
  * :func:`check_copyright` — does a media fingerprint collide with a protected
    fingerprint (a copyright claim)?

Everything returns :class:`ComplianceIssue` objects using the shared
:class:`~content_factory.models.IssueSeverity` scale, so a client can render
them with the same rules as the script linter and timeline validator.
"""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from pathlib import Path

from .models import IssueSeverity


@dataclass(frozen=True)
class PlatformRule:
    """Hard and soft limits for one publishing platform."""

    name: str
    max_duration_seconds: float | None
    min_duration_seconds: float | None
    allowed_aspect_ratios: tuple[str, ...]
    forbidden_patterns: tuple[str, ...]
    max_words: int | None


@dataclass(frozen=True)
class ComplianceMeta:
    """Measured properties of the asset being checked."""

    duration_seconds: float | None = None
    aspect_ratio: str = ""
    words: int = 0
    text: str = ""


@dataclass(frozen=True)
class ComplianceIssue:
    """A single finding from a compliance check."""

    code: str
    severity: IssueSeverity
    message: str
    hint: str | None = None


PLATFORM_RULES: dict[str, PlatformRule] = {
    "youtube": PlatformRule(
        name="youtube",
        max_duration_seconds=3600.0,
        min_duration_seconds=None,
        allowed_aspect_ratios=("16:9", "9:16", "1:1"),
        forbidden_patterns=(),
        max_words=5000,
    ),
    "tiktok": PlatformRule(
        name="tiktok",
        max_duration_seconds=600.0,
        min_duration_seconds=None,
        allowed_aspect_ratios=("9:16", "1:1"),
        forbidden_patterns=(r"\b(subscribe now|link in bio)\b",),
        max_words=2200,
    ),
    "instagram_reels": PlatformRule(
        name="instagram_reels",
        max_duration_seconds=90.0,
        min_duration_seconds=None,
        allowed_aspect_ratios=("9:16",),
        forbidden_patterns=(),
        max_words=None,
    ),
    "facebook": PlatformRule(
        name="facebook",
        max_duration_seconds=3600.0,
        min_duration_seconds=None,
        allowed_aspect_ratios=(),
        forbidden_patterns=(),
        max_words=None,
    ),
    "shorts": PlatformRule(
        name="shorts",
        max_duration_seconds=180.0,
        min_duration_seconds=None,
        allowed_aspect_ratios=("9:16",),
        forbidden_patterns=(),
        max_words=None,
    ),
}


def check_platform(meta: ComplianceMeta, platform: str) -> list[ComplianceIssue]:
    """Return compliance issues for ``meta`` on ``platform``.

    Unknown platforms yield no issues. Duration and aspect-ratio violations are
    hard limits (ERROR); forbidden phrases and word-count overruns are soft
    warnings (WARNING).
    """
    rule = PLATFORM_RULES.get(platform)
    if rule is None:
        return []

    issues: list[ComplianceIssue] = []

    if meta.duration_seconds is not None:
        if (
            rule.max_duration_seconds is not None
            and meta.duration_seconds > rule.max_duration_seconds
        ):
            issues.append(
                ComplianceIssue(
                    code="duration_too_long",
                    severity=IssueSeverity.ERROR,
                    message=(
                        f"{rule.name} allows at most {rule.max_duration_seconds:g}s; "
                        f"asset is {meta.duration_seconds:g}s."
                    ),
                    hint=f"Trim to {rule.max_duration_seconds:g}s or less.",
                )
            )
        if (
            rule.min_duration_seconds is not None
            and meta.duration_seconds < rule.min_duration_seconds
        ):
            issues.append(
                ComplianceIssue(
                    code="duration_too_short",
                    severity=IssueSeverity.ERROR,
                    message=(
                        f"{rule.name} requires at least "
                        f"{rule.min_duration_seconds:g}s; asset is "
                        f"{meta.duration_seconds:g}s."
                    ),
                    hint=f"Extend to at least {rule.min_duration_seconds:g}s.",
                )
            )

    if meta.aspect_ratio and rule.allowed_aspect_ratios:
        if meta.aspect_ratio not in rule.allowed_aspect_ratios:
            issues.append(
                ComplianceIssue(
                    code="aspect_ratio_not_allowed",
                    severity=IssueSeverity.ERROR,
                    message=(
                        f"{rule.name} does not allow aspect ratio "
                        f"{meta.aspect_ratio!r}; allowed: "
                        f"{', '.join(rule.allowed_aspect_ratios)}."
                    ),
                    hint="Re-render in an allowed aspect ratio.",
                )
            )

    if rule.max_words is not None and meta.words > rule.max_words:
        issues.append(
            ComplianceIssue(
                code="too_many_words",
                severity=IssueSeverity.WARNING,
                message=(
                    f"{rule.name} caps scripts at {rule.max_words} words; "
                    f"this one has {meta.words}."
                ),
                hint="Cut the script to tighten pacing and retention.",
            )
        )

    for pattern in rule.forbidden_patterns:
        if re.search(pattern, meta.text, flags=re.IGNORECASE):
            issues.append(
                ComplianceIssue(
                    code="forbidden_pattern",
                    severity=IssueSeverity.WARNING,
                    message=f"{rule.name} flags the phrase matching {pattern!r}.",
                    hint="Remove the flagged phrase before publishing.",
                )
            )

    return issues


@dataclass(frozen=True)
class BrandKit:
    """The approved visual identity an asset should conform to."""

    palette: tuple[str, ...]
    fonts: tuple[str, ...]
    logo_fingerprints: tuple[str, ...]


@dataclass(frozen=True)
class BrandMeta:
    """Measured visual properties of the asset."""

    dominant_colors: tuple[str, ...] = ()
    fonts_used: tuple[str, ...] = ()
    has_logo: bool = False


# How close (in RGB Euclidean distance) a colour must be to count as on-palette.
COLOR_TOLERANCE = 30.0


def check_brand(meta: BrandMeta, kit: BrandKit) -> list[ComplianceIssue]:
    """Return brand-compliance issues for ``meta`` against ``kit``.

    A missing logo is a hard error; an off-palette dominant colour or a font
    outside the kit is a warning.
    """
    issues: list[ComplianceIssue] = []

    if not meta.has_logo:
        issues.append(
            ComplianceIssue(
                code="missing_logo",
                severity=IssueSeverity.ERROR,
                message="The asset does not carry the brand logo.",
                hint="Overlay the approved logo before exporting.",
            )
        )

    for color in meta.dominant_colors:
        if not any(
            hex_distance(color, kit_color) <= COLOR_TOLERANCE
            for kit_color in kit.palette
        ):
            issues.append(
                ComplianceIssue(
                    code="off_palette",
                    severity=IssueSeverity.WARNING,
                    message=f"Dominant colour {color!r} is off the brand palette.",
                    hint="Recolour toward one of the approved palette swatches.",
                )
            )

    for font in meta.fonts_used:
        if font not in kit.fonts:
            issues.append(
                ComplianceIssue(
                    code="font_not_in_kit",
                    severity=IssueSeverity.WARNING,
                    message=f"Font {font!r} is not in the brand kit.",
                    hint=f"Use one of: {', '.join(kit.fonts) or '(none)'}.",
                )
            )

    return issues


def check_copyright(
    media_fingerprint: str, protected_fingerprints: tuple[str, ...]
) -> list[ComplianceIssue]:
    """Flag an exact fingerprint collision with a protected work."""
    if media_fingerprint in protected_fingerprints:
        return [
            ComplianceIssue(
                code="copyright_match",
                severity=IssueSeverity.ERROR,
                message="Media fingerprint matches a protected/copyrighted work.",
                hint="Do not publish; source a licensed or original asset instead.",
            )
        ]
    return []


def fingerprint_music_audio(path: str) -> str:
    """Return a sha256 content hash of the audio file at ``path``.

    Raises :class:`ValueError` when the file does not exist.
    """
    file_path = Path(path)
    if not file_path.is_file():
        raise ValueError(f"audio file not found: '{path}'")
    return hashlib.sha256(file_path.read_bytes()).hexdigest()


def hex_distance(a: str, b: str) -> float:
    """Euclidean distance between two hex colours in RGB space."""
    ar, ag, ab = _parse_hex(a)
    br, bg, bb = _parse_hex(b)
    return math.sqrt(float((ar - br) ** 2 + (ag - bg) ** 2 + (ab - bb) ** 2))


def _parse_hex(color: str) -> tuple[int, int, int]:
    """Parse ``#rgb`` / ``#rrggbb`` (leading ``#`` optional) into RGB ints."""
    value = color.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    red = int(value[0:2], 16)
    green = int(value[2:4], 16)
    blue = int(value[4:6], 16)
    return red, green, blue
