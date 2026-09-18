"""Tests for the script intelligence module."""

from __future__ import annotations

from content_factory.models import ResearchBundle, ResearchSource, ScriptIssueSeverity
from content_factory.presets import PresetLibrary
from content_factory.script_engine import (
    COPY_RUN_WORDS,
    analyze_script,
    build_script_prompt,
    count_units,
    estimate_speech_seconds,
    language_profile,
    lint_script,
    longest_shared_run,
    parse_script,
    plan_script,
    style_directives,
)

SCRIPT = """[Hook]
Why does the city sound different at 5am?

[Context]
Delivery trucks and shutters set the rhythm before people arrive.

[Turn]
The quiet hour is the only time the machinery is visible.

[Payoff]
That is the real heartbeat of a place.

[CTA]
Follow for more stories like this.
"""


def test_parse_script_reads_bracketed_sections() -> None:
    sections = parse_script(SCRIPT)
    assert [section.label for section in sections] == [
        "Hook",
        "Context",
        "Turn",
        "Payoff",
        "CTA",
    ]
    assert all(section.text for section in sections)


def test_parse_script_falls_back_to_paragraphs() -> None:
    sections = parse_script("First paragraph.\n\nSecond paragraph.")
    assert [section.label for section in sections] == ["Scene 1", "Scene 2"]


def test_parse_script_handles_empty_input() -> None:
    assert parse_script(None) == []
    assert parse_script("   ") == []


def test_count_units_strips_markers() -> None:
    assert count_units("[Hook] one two three", "en") == 3
    assert count_units("", "en") == 0


def test_count_units_is_character_based_for_cjk() -> None:
    # こ れ は テ ス ト で す → 8 characters, no whitespace to split on.
    assert count_units("これはテストです", "ja") == 8


def test_language_profile_falls_back_for_unknown_codes() -> None:
    assert language_profile("vi-VN").code == "vi"
    assert language_profile("xx").code == "und"


def test_estimate_speech_seconds_is_positive_and_scales() -> None:
    short = estimate_speech_seconds("one two three", "en")
    long = estimate_speech_seconds("one two three four five six seven eight", "en")
    assert 0 < short < long


def test_plan_script_reports_sections_and_target_fit() -> None:
    plan = plan_script(SCRIPT, language="en", target_seconds=30)
    assert len(plan.sections) == 5
    assert plan.sections[0].label == "Hook"
    assert plan.estimated_seconds > 0
    assert 0.0 < plan.sections[0].share <= 1.0
    assert plan.speech_units_per_second > 0


def test_plan_script_warns_when_narration_is_too_short() -> None:
    plan = plan_script("[Hook]\nShort.", language="en", target_seconds=90)
    assert plan.fits_target is False
    assert any("short of the" in warning for warning in plan.warnings)


def test_plan_script_warns_without_section_markers() -> None:
    plan = plan_script("A single paragraph with no markers at all.", target_seconds=10)
    assert any("markers" in warning for warning in plan.warnings)


def test_longest_shared_run_detects_verbatim_overlap() -> None:
    source = (
        "Sudden movement, a question, or an unresolved image interrupts the "
        "scrolling behaviour of viewers everywhere."
    )
    script = (
        "Viewers stay when a question or an unresolved image interrupts the scroll."
    )
    run, phrase = longest_shared_run(script, [source])
    assert run >= 5
    assert phrase


def test_longest_shared_run_ignores_short_overlap() -> None:
    run, _ = longest_shared_run("Completely novel wording here.", ["Different text"])
    assert run == 0


def test_lint_flags_long_sentences_and_banned_phrases() -> None:
    style = PresetLibrary().resolve("viral-short")
    script = (
        "[Hook] In this video we will explore how the attention economy shapes "
        "the way that modern short-form video platforms reward creators who "
        "optimize their opening seconds for retention above everything else."
    )
    issues = lint_script(script, language="en", style=style)
    codes = {issue.code for issue in issues}
    assert "banned_phrase" in codes
    assert "long_sentence" in codes


def test_lint_flags_copy_risk_as_error() -> None:
    research = ResearchBundle(
        sources=[
            ResearchSource(
                id="s1",
                title="Source",
                url="https://example.test",
                source_type="article",
                summary=(
                    "Most viewers drop in the first five seconds and the hook is "
                    "the funnel that decides whether they stay or swipe away."
                ),
            )
        ]
    )
    script = (
        "[Hook]\nMost viewers drop in the first five seconds and the hook is the "
        "funnel.\n"
    )
    issues = lint_script(script, language="en", research=research)
    copy_issues = [issue for issue in issues if issue.code.startswith("copy_risk")]
    assert copy_issues
    assert any(issue.severity == ScriptIssueSeverity.ERROR for issue in copy_issues)
    assert COPY_RUN_WORDS <= 20


def test_lint_flags_missing_hook_curiosity() -> None:
    issues = lint_script("[Hook]\nJust an ordinary statement.", language="en")
    assert any(issue.code == "weak_hook" for issue in issues)


def test_analyze_script_scores_findings() -> None:
    good = analyze_script(SCRIPT, language="en", target_seconds=30, research=None)
    bad = analyze_script("", language="en", target_seconds=30)
    assert good.score > bad.score
    assert bad.score < 100
    assert any(issue.code == "empty_script" for issue in bad.issues)


def test_style_directives_include_structure_and_cta() -> None:
    style = PresetLibrary().resolve("viral-short")
    directives = style_directives(style, "vi")
    assert "[Hook]" in directives
    assert "Vietnamese" in directives or "âm tiết" in directives
    assert "Banned phrases" not in directives
    assert "Never use these phrases" in directives


def test_build_script_prompt_keeps_the_template_contract() -> None:
    style = PresetLibrary().resolve("viral-short")
    research = ResearchBundle(
        sources=[
            ResearchSource(
                id="s1",
                title="Attention",
                url="https://example.test",
                source_type="article",
                summary="Attention is scarce.",
                highlights=["The first three seconds decide."],
            )
        ],
        key_facts=["Attention is the scarce resource."],
    )
    prompt = build_script_prompt(
        topic="Morning light",
        language="vi",
        target_seconds=45,
        style=style,
        research=research,
        reference_notes="Fast cuts, caption-heavy, no music bed.",
        extra_directives=["Do not mention brand names."],
    )
    assert prompt.startswith("Topic: Morning light\n")
    assert "\nLanguage: vi\n" in prompt
    assert "Target duration: 45 seconds" in prompt
    assert "Key facts:\n- Attention is the scarce resource." in prompt
    assert "[Hook]" in prompt
    assert "Do not mention brand names." in prompt
    assert "Reference video notes" in prompt


def test_build_script_prompt_accepts_grounding_keyword() -> None:
    """Regression lock for the P1 concurrent-import anomaly.

    A stale bytecode cache once shipped a ``build_script_prompt`` without the
    ``grounding`` keyword, so ``service._build_prompt`` failed with a TypeError
    whenever the module was imported from a poisoned ``__pycache__``. Lock the
    signature and prove a grounding bundle actually renders.
    """
    import inspect

    from content_factory.models import GroundingBundle

    params = inspect.signature(build_script_prompt).parameters
    assert "grounding" in params, params
    assert params["grounding"].kind == inspect.Parameter.KEYWORD_ONLY

    style = PresetLibrary().resolve("viral-short")
    grounding = GroundingBundle(
        query="Battle of Stalingrad",
        context_text="[1] The battle lasted from August 1942 to February 1943.",
        hits=[],
    )
    prompt = build_script_prompt(
        topic="Battle of Stalingrad",
        language="en",
        target_seconds=45,
        style=style,
        grounding=grounding,
    )
    assert "Knowledge base (cite as [n] in your own words)" in prompt
    assert "[1] The battle lasted from August 1942 to February 1943." in prompt
