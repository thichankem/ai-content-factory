"""Tests for the user-tunable script-style preset library."""

from __future__ import annotations

import json
from pathlib import Path

from content_factory.models import ScriptStyle
from content_factory.presets import (
    BUILTIN_STYLES,
    PresetLibrary,
    style_from_markdown,
    style_to_markdown,
)


def test_builtin_styles_are_available(tmp_path: Path) -> None:
    library = PresetLibrary(tmp_path)
    names = library.names()
    for style in BUILTIN_STYLES:
        assert style.name in names
    assert all(style.builtin for style in library.list_styles() if style.name in names)


def test_resolve_falls_back_to_default(tmp_path: Path) -> None:
    library = PresetLibrary(tmp_path)
    assert library.resolve("does-not-exist").name == "viral-short"
    assert library.resolve(None).name == "viral-short"


def test_get_is_case_insensitive(tmp_path: Path) -> None:
    library = PresetLibrary(tmp_path)
    assert library.get("VIRAL-SHORT") is not None
    assert library.get("") is None


def test_save_and_reload_json_preset(tmp_path: Path) -> None:
    library = PresetLibrary(tmp_path)
    style = ScriptStyle(
        name="my-vertical",
        title="My vertical style",
        tone="dry and fast",
        banned_phrases=["hello world"],
        sentence_max_units=9,
    )
    saved = library.save(style)
    assert saved.builtin is False
    assert (tmp_path / "my-vertical.json").is_file()

    reloaded = PresetLibrary(tmp_path).get("my-vertical")
    assert reloaded is not None
    assert reloaded.title == "My vertical style"
    assert reloaded.sentence_max_units == 9
    assert reloaded.banned_phrases == ["hello world"]
    assert reloaded.builtin is False


def test_saved_preset_overrides_builtin(tmp_path: Path) -> None:
    library = PresetLibrary(tmp_path)
    library.save(ScriptStyle(name="viral-short", tone="whispered"))
    library.reload()
    resolved = library.resolve("viral-short")
    assert resolved.tone == "whispered"
    assert resolved.builtin is False


def test_builtin_presets_cannot_be_deleted(tmp_path: Path) -> None:
    library = PresetLibrary(tmp_path)
    assert library.delete("viral-short") is False
    assert library.get("viral-short") is not None


def test_user_preset_can_be_deleted(tmp_path: Path) -> None:
    library = PresetLibrary(tmp_path)
    library.save(ScriptStyle(name="temp-style"))
    assert library.delete("temp-style") is True
    assert library.get("temp-style") is None


def test_markdown_round_trip_preserves_fields() -> None:
    original = ScriptStyle(
        name="docu",
        title="Docu",
        description="Measured narration.",
        tone="calm",
        structure=["Hook", "Evidence", "Payoff"],
        hook_rules=["Start with an image."],
        banned_phrases=["game changer"],
        cta="Subscribe for more.",
        sentence_max_units=18,
        max_sections=9,
        language_notes={"vi": "Câu ngắn."},
        units_per_second={"vi": 2.9},
    )
    restored = style_from_markdown(style_to_markdown(original))
    assert restored.name == "docu"
    assert restored.structure == ["Hook", "Evidence", "Payoff"]
    assert restored.hook_rules == ["Start with an image."]
    assert restored.banned_phrases == ["game changer"]
    assert restored.language_notes == {"vi": "Câu ngắn."}
    assert restored.units_per_second == {"vi": 2.9}
    assert restored.sentence_max_units == 18
    assert restored.max_sections == 9
    assert restored.builtin is False


def test_markdown_preset_file_is_loaded(tmp_path: Path) -> None:
    (tmp_path / "doc-style.md").write_text(
        "\n".join(
            [
                "# Style: doc-style",
                "",
                "title: Doc style",
                "tone: neutral",
                "sentence_max_units: 12",
                "",
                "## Structure",
                "- Hook",
                "- Body",
                "",
                "## Hook rules",
                "- Lead with a fact.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    library = PresetLibrary(tmp_path)
    style = library.get("doc-style")
    assert style is not None
    assert style.tone == "neutral"
    assert style.structure == ["Hook", "Body"]
    assert style.sentence_max_units == 12
    assert style.builtin is False


def test_invalid_files_are_ignored(tmp_path: Path) -> None:
    (tmp_path / "broken.json").write_text("{ not json", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("ignored", encoding="utf-8")
    library = PresetLibrary(tmp_path)
    assert "broken" not in library.names()
    assert "notes" not in library.names()


def test_export_markdown_returns_none_for_unknown(tmp_path: Path) -> None:
    library = PresetLibrary(tmp_path)
    assert library.export_markdown("nope") is None
    markdown = library.export_markdown("story")
    assert markdown is not None
    assert "# Style: story" in markdown


def test_saved_json_is_human_readable(tmp_path: Path) -> None:
    library = PresetLibrary(tmp_path)
    library.save(ScriptStyle(name="readable", title="Readable"))
    payload = json.loads((tmp_path / "readable.json").read_text(encoding="utf-8"))
    assert payload["name"] == "readable"
    assert payload["builtin"] is False
