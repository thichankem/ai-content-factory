"""User-tunable scripting presets.

Every scripting decision in the pipeline is driven by a
:class:`~content_factory.models.ScriptStyle`. A handful of presets ship with
the package so the pipeline works out of the box; operators can override a
built-in preset or add brand-new ones by dropping a file into the presets
directory (``CONTENT_FACTORY_PRESETS_DIR``, default ``./presets``).

Two file formats are supported:

* ``<slug>.json`` — the canonical, lossless form.
* ``<slug>.md`` — a human/agent-friendly form that round-trips the same
  fields, so an external AI agent can edit the style contract as Markdown.

Nothing here touches the network or the filesystem at import time; the
directory is scanned when the library is constructed and on demand.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from .models import ScriptStyle

logger = logging.getLogger("content_factory.presets")

#: Built-in presets. These are always available and can be overridden by a
#: user file with the same slug.
BUILTIN_STYLES: tuple[ScriptStyle, ...] = (
    ScriptStyle(
        name="viral-short",
        title="Viral short (TikTok / Reels / Shorts)",
        description=(
            "Pattern-interrupt hook, fast beats, one idea per scene, explicit "
            "payoff, strong call to action."
        ),
        tone="punchy, second person, high energy, no filler",
        structure=["Hook", "Context", "Turn", "Payoff", "CTA"],
        hook_rules=[
            "Open with tension in the first 8 words.",
            "Use a concrete number, stake, or contradiction — never a generic "
            "greeting.",
            "Never start with 'In this video' or 'Today we will'.",
        ],
        sentence_max_units=12,
        cta="Follow for more stories like this.",
        banned_phrases=[
            "in this video",
            "today we will",
            "let's dive in",
            "as we all know",
            "trong video này",
            "hôm nay chúng ta sẽ",
        ],
        language_notes={
            "vi": "Dùng câu ngắn, khẩu ngữ tự nhiên; tránh từ Hán-Việt nặng.",
        },
        max_sections=9,
    ),
    ScriptStyle(
        name="documentary",
        title="Documentary voiceover",
        description=(
            "Measured, observational narration. Evidence leads, emotion "
            "follows. Scene changes drive the reveal."
        ),
        tone="calm, authoritative, cinematic, third person",
        structure=["Hook", "Context", "Evidence", "Turn", "Payoff"],
        hook_rules=[
            "Start with a specific image or moment, not a claim.",
            "Establish time and place within the first two sentences.",
        ],
        sentence_max_units=20,
        cta="",
        banned_phrases=["in this video", "as we all know"],
        max_sections=14,
    ),
    ScriptStyle(
        name="educational",
        title="Educational explainer",
        description=(
            "Teach one idea end to end: promise, mechanism, proof, recap. "
            "Clarity beats drama."
        ),
        tone="clear, friendly, expert-but-plain",
        structure=["Hook", "Promise", "Mechanism", "Proof", "Recap", "CTA"],
        hook_rules=[
            "Name the benefit the viewer gets in the first sentence.",
            "Pose the question the viewer is already asking.",
        ],
        sentence_max_units=18,
        cta="Save this so you can come back to it.",
        banned_phrases=["in this video", "obviously", "just simply"],
        max_sections=12,
    ),
    ScriptStyle(
        name="story",
        title="Micro story",
        description=(
            "A 40-second arc: ordinary setup, a turn that reframes it, and a "
            "payoff that lands."
        ),
        tone="warm, intimate, first person, sensory",
        structure=["Hook", "Setup", "Turn", "Payoff"],
        hook_rules=[
            "Open mid-action — start after the story has already begun.",
            "Withhold the outcome the viewer will want.",
        ],
        sentence_max_units=14,
        cta="",
        banned_phrases=["once upon a time"],
        max_sections=8,
    ),
    ScriptStyle(
        name="product-review",
        title="Product review",
        description=(
            "Honest verdict first, then the evidence that supports it, then "
            "who it is for."
        ),
        tone="direct, balanced, no hype, no superlatives without proof",
        structure=["Verdict", "Proof", "Tradeoffs", "Who it is for", "CTA"],
        hook_rules=[
            "Lead with the verdict, then justify it.",
            "Name one real downside in the first half.",
        ],
        sentence_max_units=16,
        cta="Comment what you want reviewed next.",
        banned_phrases=["game changer", "literally the best", "must buy"],
        max_sections=10,
    ),
)

DEFAULT_STYLE = "viral-short"


def builtin_styles() -> list[ScriptStyle]:
    """Return fresh copies of the built-in presets."""
    return [style.model_copy(deep=True) for style in BUILTIN_STYLES]


def style_to_markdown(style: ScriptStyle) -> str:
    """Render a preset as Markdown an external agent can read and edit."""
    lines = [
        f"# Style: {style.name}",
        "",
        f"title: {style.title}",
        f"description: {style.description}",
        f"tone: {style.tone}",
        f"cta: {style.cta}",
        f"sentence_max_units: {style.sentence_max_units}",
        f"max_sections: {style.max_sections}",
        "",
        "## Structure",
        *[f"- {item}" for item in style.structure],
        "",
        "## Hook rules",
        *([f"- {item}" for item in style.hook_rules] or ["- "]),
        "",
        "## Banned phrases",
        *([f"- {item}" for item in style.banned_phrases] or ["- "]),
        "",
        "## Language notes",
        *(
            [f"- {key}: {value}" for key, value in style.language_notes.items()]
            or ["- "]
        ),
        "",
        "## Speech rate overrides",
        *(
            [f"- {key}: {value}" for key, value in style.units_per_second.items()]
            or ["- "]
        ),
        "",
    ]
    return "\n".join(lines)


def style_from_markdown(text: str, *, name: str | None = None) -> ScriptStyle:
    """Parse a Markdown preset produced by :func:`style_to_markdown`.

    The parser is deliberately forgiving: unknown keys are ignored and missing
    keys fall back to the model defaults, so an agent can return a partial
    style document without breaking the pipeline.
    """
    data: dict[str, Any] = {}
    bullets: dict[str, list[str]] = {
        "structure": [],
        "hook_rules": [],
        "banned_phrases": [],
    }
    language_notes: dict[str, str] = {}
    rates: dict[str, float] = {}

    section: str | None = None
    _SECTION_KEYS = {
        "structure": "structure",
        "hook rules": "hook_rules",
        "banned phrases": "banned_phrases",
        "language notes": "language_notes",
        "speech rate overrides": "units_per_second",
    }

    for raw_line in (text or "").splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        heading = re.match(r"^#{1,6}\s*(?:Style:\s*)?(.+?)\s*$", stripped)
        if heading:
            key = heading.group(1).lower()
            if key in _SECTION_KEYS:
                section = _SECTION_KEYS[key]
            elif stripped.startswith("# Style:"):
                data.setdefault("name", heading.group(1).strip())
                section = None
            else:
                section = None
            continue
        if stripped.startswith(("-", "*")):
            item = stripped.lstrip("-* ").strip()
            if not item:
                continue
            if section == "language_notes":
                key, _, value = item.partition(":")
                if key.strip():
                    language_notes[key.strip()] = value.strip()
            elif section == "units_per_second":
                key, _, value = item.partition(":")
                try:
                    rates[key.strip()] = float(value.strip())
                except ValueError:
                    continue
            elif section in bullets:
                bullets[section].append(item)
            continue
        key, sep, value = stripped.partition(":")
        if not sep:
            continue
        key = key.strip().lower().replace(" ", "_")
        value = value.strip()
        if key in {"sentence_max_units", "max_sections"}:
            try:
                data[key] = int(float(value))
            except ValueError:
                continue
        else:
            data[key] = value

    declared_name = str(data.pop("name", "") or "").strip()
    payload: dict[str, Any] = {
        "name": declared_name or (name or "custom"),
        "title": data.pop("title", ""),
        "description": data.pop("description", ""),
        "tone": data.pop("tone", ScriptStyle.model_fields["tone"].default),
        "cta": data.pop("cta", ""),
        "builtin": False,
    }
    for key, value in data.items():
        if key in ScriptStyle.model_fields:
            payload[key] = value
    if bullets["structure"]:
        payload["structure"] = bullets["structure"]
    if bullets["hook_rules"]:
        payload["hook_rules"] = bullets["hook_rules"]
    if bullets["banned_phrases"]:
        payload["banned_phrases"] = bullets["banned_phrases"]
    if language_notes:
        payload["language_notes"] = language_notes
    if rates:
        payload["units_per_second"] = rates
    style = ScriptStyle.model_validate(payload)
    if not style.title:
        style.title = style.name.replace("-", " ").title()
    return style


class PresetLibrary:
    """Loads built-in presets and any user overrides found on disk."""

    def __init__(self, directory: str | Path | None = None) -> None:
        self._dir = Path(directory) if directory else None
        self._styles: dict[str, ScriptStyle] = {}
        self.reload()

    @property
    def directory(self) -> Path | None:
        return self._dir

    def reload(self) -> None:
        """Rebuild the catalog: built-ins first, then on-disk overrides."""
        styles: dict[str, ScriptStyle] = {
            style.slug: style.model_copy(deep=True) for style in BUILTIN_STYLES
        }
        if self._dir is not None and self._dir.is_dir():
            for path in sorted(self._dir.iterdir()):
                style = self._load_file(path)
                if style is not None:
                    styles[style.slug] = style
        self._styles = styles

    def _load_file(self, path: Path) -> ScriptStyle | None:
        suffix = path.suffix.lower()
        if suffix not in {".json", ".md", ".markdown"}:
            return None
        try:
            text = path.read_text(encoding="utf-8")
            if suffix == ".json":
                style = ScriptStyle.model_validate(json.loads(text))
                style.builtin = False
            else:
                style = style_from_markdown(text, name=path.stem)
            style.name = style.name or path.stem
            return style
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Ignoring invalid preset %s: %s", path, exc)
            return None

    def names(self) -> list[str]:
        return sorted(self._styles)

    def list_styles(self) -> list[ScriptStyle]:
        """Return every known preset, user presets first."""
        return sorted(
            (style.model_copy(deep=True) for style in self._styles.values()),
            key=lambda style: (style.builtin, style.name),
        )

    def get(self, name: str | None) -> ScriptStyle | None:
        """Look a preset up by slug or by display name (case-insensitive)."""
        if not name:
            return None
        key = re.sub(r"[^a-z0-9-]+", "-", name.lower()).strip("-")
        found = self._styles.get(key)
        if found is None:
            for style in self._styles.values():
                if style.name.lower() == name.lower():
                    found = style
                    break
        return found.model_copy(deep=True) if found is not None else None

    def resolve(self, name: str | None) -> ScriptStyle:
        """Return the requested preset, falling back to the default."""
        return self.get(name) or self.get(DEFAULT_STYLE) or builtin_styles()[0]

    def save(self, style: ScriptStyle) -> ScriptStyle:
        """Persist a preset as JSON, creating the directory if needed."""
        if self._dir is None:
            raise RuntimeError("No presets directory is configured.")
        self._dir.mkdir(parents=True, exist_ok=True)
        style.builtin = False
        path = self._dir / f"{style.slug}.json"
        path.write_text(
            json.dumps(style.model_dump(mode="json"), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        self._styles[style.slug] = style.model_copy(deep=True)
        return style

    def export_markdown(self, name: str) -> str | None:
        """Render a preset as Markdown for an external agent to edit."""
        style = self.get(name)
        return style_to_markdown(style) if style is not None else None

    def delete(self, name: str) -> bool:
        """Delete a user preset file. Built-ins cannot be deleted."""
        style = self.get(name)
        if style is None or style.builtin:
            return False
        if self._dir is None:
            return False
        removed = False
        for suffix in (".json", ".md", ".markdown"):
            path = self._dir / f"{style.slug}{suffix}"
            if path.is_file():
                path.unlink()
                removed = True
        self._styles.pop(style.slug, None)
        return removed
