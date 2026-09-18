"""Script intelligence: parsing, timing, linting, and prompt construction.

This module is the single source of truth for everything that happens between
a topic and an approved narration script:

* :func:`parse_script` splits a script into labelled sections (``[Hook]``,
  ``[Turn]``, ...) regardless of who wrote it — a human, the built-in template,
  Claude, Gemini, DeepSeek, or an external coding agent.
* :func:`plan_script` estimates how long the narration will take in the target
  language and reports whether it fits the requested duration.
* :func:`lint_script` finds quality and compliance problems, including
  verbatim overlap with the research sources (the project's core "learn, don't
  copy" guarantee).
* :func:`build_script_prompt` renders a strong, contract-style prompt aimed at
  high-end models such as Claude: explicit role, hard constraints, grounding
  material, and an unambiguous output contract.

Everything here is pure and synchronous so it can be tested directly and reused
by the API, the worker, and the external-agent bridge.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from .models import (
    GroundingBundle,
    ResearchBundle,
    ScriptAnalysis,
    ScriptIssue,
    ScriptIssueSeverity,
    ScriptPlan,
    ScriptSectionInfo,
    ScriptStyle,
    utcnow,
)
from .text import word_tokens

#: Pause inserted between narrated sections when estimating total runtime.
PAUSE_SECONDS_PER_SECTION = 0.25

#: How far the estimate may drift from the target before we warn.
_TOLERANCE = 0.15

#: Minimum length of a shared word run that counts as verbatim copying.
COPY_RUN_WORDS = 8

#: Hard cap so the overlap scan stays linear on long scripts.
_MAX_RUN_WORDS = 40

_SECTION_RE = re.compile(r"^\s*\[([^\]]+)\]\s*$", re.MULTILINE)

#: Bracketed marker at the start of a line, with or without trailing text.
_LEADING_MARKER_RE = re.compile(r"^\s*\[[^\]]{1,60}\]\s*", re.MULTILINE)
_WORD_RE = re.compile(r"\w+", re.UNICODE)
_CJK_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af]")

#: Matches sentence terminators in both Latin and CJK scripts.
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?…。！？])\s+|\n+")

_CURIOSITY_MARKERS = (
    "?",
    "why",
    "how",
    "what",
    "what if",
    "the reason",
    "secret",
    "nobody",
    "never",
    "most people",
    "vì sao",
    "tại sao",
    "bí mật",
    "không ai",
    "sự thật",
)


@dataclass(frozen=True)
class LanguageProfile:
    """Speech characteristics of one language."""

    code: str
    label: str
    units_per_second: float
    sentence_max_units: int
    char_based: bool = False
    unit_name: str = "words"


#: Per-language speech rates. Tuned conservatively for neural TTS voices.
LANGUAGE_PROFILES: dict[str, LanguageProfile] = {
    "vi": LanguageProfile("vi", "Vietnamese", 2.7, 16, unit_name="âm tiết"),
    "en": LanguageProfile("en", "English", 2.6, 18),
    "fr": LanguageProfile("fr", "French", 2.6, 18),
    "de": LanguageProfile("de", "German", 2.4, 18),
    "es": LanguageProfile("es", "Spanish", 2.8, 18),
    "pt": LanguageProfile("pt", "Portuguese", 2.6, 18),
    "it": LanguageProfile("it", "Italian", 2.7, 18),
    "nl": LanguageProfile("nl", "Dutch", 2.5, 18),
    "pl": LanguageProfile("pl", "Polish", 2.5, 18),
    "ru": LanguageProfile("ru", "Russian", 2.5, 18),
    "tr": LanguageProfile("tr", "Turkish", 2.5, 16),
    "id": LanguageProfile("id", "Indonesian", 2.6, 16),
    "th": LanguageProfile(
        "th", "Thai", 3.0, 20, char_based=True, unit_name="characters"
    ),
    "ja": LanguageProfile(
        "ja", "Japanese", 4.0, 30, char_based=True, unit_name="characters"
    ),
    "ko": LanguageProfile(
        "ko", "Korean", 3.4, 30, char_based=True, unit_name="characters"
    ),
    "zh": LanguageProfile(
        "zh", "Chinese", 4.2, 30, char_based=True, unit_name="characters"
    ),
}

_FALLBACK_PROFILE = LanguageProfile("und", "the target language", 2.5, 18)


@dataclass(frozen=True)
class ScriptSection:
    """One labelled section of a script, before timing is applied."""

    index: int
    label: str
    text: str


def language_profile(language: str) -> LanguageProfile:
    """Return the speech profile for a language code (``vi``, ``vi-VN``, ...)."""
    code = (language or "").split("-")[0].strip().lower()
    return LANGUAGE_PROFILES.get(code, _FALLBACK_PROFILE)


def count_units(text: str, language: str = "en") -> int:
    """Count speech units (words, or characters for CJK/Thai scripts)."""
    cleaned = _strip_markers(text)
    if not cleaned:
        return 0
    profile = language_profile(language)
    if profile.char_based:
        return len(_CJK_RE.findall(cleaned)) or len(_WORD_RE.findall(cleaned))
    return len(_WORD_RE.findall(cleaned))


def estimate_speech_seconds(
    text: str, language: str = "en", ups: float | None = None
) -> float:
    """Estimate how long ``text`` takes to narrate."""
    units = count_units(text, language)
    if units == 0:
        return 0.0
    rate = ups or language_profile(language).units_per_second
    return round(units / max(0.5, rate), 2)


def _strip_markers(text: str) -> str:
    """Drop ``[Section]`` markers and markdown noise before counting."""
    without_markers = _LEADING_MARKER_RE.sub(" ", text or "")
    without_markdown = re.sub(
        r"^\s*(#{1,6}|[*\-]|\d+\.)\s*", "", without_markers, flags=re.MULTILINE
    )
    return re.sub(r"\s+", " ", without_markdown).strip()


def parse_script(script: str | None) -> list[ScriptSection]:
    """Split a script into labelled sections.

    Recognizes ``[Section]`` markers; falls back to blank-line paragraphs and
    finally to a single unnamed section, so any input yields a usable plan.
    """
    raw = script or ""
    sections: list[ScriptSection] = []
    label: str | None = None
    buffer: list[str] = []

    for line in raw.splitlines():
        match = _SECTION_RE.match(line.strip())
        if match:
            if label is not None:
                sections.append(_make_section(len(sections), label, buffer))
            label = match.group(1).strip()
            buffer = []
        elif line.strip():
            buffer.append(line.strip())
    if label is not None:
        sections.append(_make_section(len(sections), label, buffer))

    if not sections:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", raw) if p.strip()]
        sections = [
            ScriptSection(index=index, label=f"Scene {index + 1}", text=paragraph)
            for index, paragraph in enumerate(paragraphs)
        ]
    if not sections:
        text = raw.strip()
        if text:
            sections = [ScriptSection(index=0, label="Scene 1", text=text)]
    return sections


def _make_section(index: int, label: str, buffer: list[str]) -> ScriptSection:
    return ScriptSection(index=index, label=label, text=" ".join(buffer).strip())


def sentences(text: str) -> list[str]:
    """Split text into sentences for readability checks."""
    cleaned = _strip_markers(text)
    if not cleaned:
        return []
    return [part.strip() for part in _SENTENCE_SPLIT_RE.split(cleaned) if part.strip()]


def resolve_rate(language: str, style: ScriptStyle | None = None) -> float:
    """Speech rate for a language, honouring per-style overrides."""
    code = (language or "en").split("-")[0].strip().lower()
    if style and code in style.units_per_second:
        return max(0.5, float(style.units_per_second[code]))
    return language_profile(language).units_per_second


def plan_script(
    script: str | None,
    *,
    language: str = "en",
    target_seconds: int = 45,
    style: ScriptStyle | None = None,
) -> ScriptPlan:
    """Estimate the narrated runtime of a script section by section."""
    sections = parse_script(script)
    rate = resolve_rate(language, style)
    target = max(1, int(target_seconds))

    infos: list[ScriptSectionInfo] = []
    total = 0.0
    for section in sections:
        units = count_units(section.text, language)
        seconds = round(units / rate, 2) if units else 0.0
        total += seconds
        infos.append(
            ScriptSectionInfo(
                index=section.index,
                label=section.label,
                text=section.text,
                unit_count=units,
                estimated_seconds=seconds,
                share=0.0,
            )
        )
    if infos:
        total += PAUSE_SECONDS_PER_SECTION * (len(infos) - 1)
    total = round(total, 2)
    for info in infos:
        info.share = round(info.estimated_seconds / total, 3) if total else 0.0

    warnings: list[str] = []
    has_markers = bool(_SECTION_RE.search(script or ""))
    if not has_markers:
        warnings.append(
            "No [Section] markers found; using paragraph splits. Add markers "
            "(e.g. [Hook]) so the script maps cleanly onto scenes."
        )
    if style is not None and len(infos) > style.max_sections:
        warnings.append(
            f"{len(infos)} sections exceed the '{style.name}' budget of "
            f"{style.max_sections}; consider merging beats."
        )
    low = target * (1.0 - _TOLERANCE)
    high = target * (1.0 + _TOLERANCE)
    if total and total < low:
        warnings.append(
            f"Narration is about {round(low - total, 1)}s short of the "
            f"{target}s target; add a beat or expand the payoff."
        )
    elif total > high:
        warnings.append(
            f"Narration is about {round(total - high, 1)}s over the {target}s "
            "target; cut a beat or tighten the sentences."
        )

    return ScriptPlan(
        language=language or "en",
        target_seconds=target,
        estimated_seconds=total,
        fits_target=bool(total) and low <= total <= high,
        speech_units_per_second=rate,
        sections=infos,
        warnings=warnings,
        generated_at=utcnow(),
    )


def longest_shared_run(text: str, sources: Iterable[str]) -> tuple[int, str]:
    """Longest run of consecutive words shared with any source.

    Returns ``(length_in_words, offending_phrase)``. Used to guarantee the
    script transforms its sources instead of reproducing them.
    """
    words = word_tokens(text)
    if not words:
        return 0, ""
    haystacks: list[list[str]] = []
    for source in sources:
        source_words = word_tokens(source)
        if source_words:
            haystacks.append(source_words)

    best_len = 0
    best_phrase = ""
    for haystack in haystacks:
        if len(haystack) < 3:
            continue
        window = 3
        while window <= min(len(words), _MAX_RUN_WORDS):
            hit: str | None = None
            joined = " ".join(haystack)
            for start in range(0, len(words) - window + 1):
                candidate = " ".join(words[start : start + window])
                if candidate in joined:
                    hit = candidate
                    break
            if hit is None:
                break
            best_len = window
            best_phrase = hit
            window += 1
    return best_len, best_phrase


def lint_script(
    script: str | None,
    *,
    language: str = "en",
    target_seconds: int = 45,
    style: ScriptStyle | None = None,
    research: ResearchBundle | None = None,
    plan: ScriptPlan | None = None,
) -> list[ScriptIssue]:
    """Return quality and compliance findings for a script."""
    issues: list[ScriptIssue] = []
    sections = parse_script(script)
    plan = plan or plan_script(
        script, language=language, target_seconds=target_seconds, style=style
    )
    body = _strip_markers(script or "")
    if not body:
        return [
            ScriptIssue(
                code="empty_script",
                severity=ScriptIssueSeverity.ERROR,
                message="The script is empty.",
                hint="Draft a script or import one from an external agent.",
            )
        ]

    max_units = (
        style.sentence_max_units
        if style
        else language_profile(language).sentence_max_units
    )
    first = sections[0] if sections else None
    hook_text = (first.text if first else body).lower()
    if not any(marker in hook_text for marker in _CURIOSITY_MARKERS):
        issues.append(
            ScriptIssue(
                code="weak_hook",
                severity=ScriptIssueSeverity.WARNING,
                message="The opening line has no question, stake, or number.",
                hint="Add tension in the first 8 words to stop the scroll.",
            )
        )
    if first is not None and count_units(first.text, language) > max_units * 1.5:
        issues.append(
            ScriptIssue(
                code="long_hook",
                severity=ScriptIssueSeverity.WARNING,
                message="The hook runs long for a short-form opening.",
                hint=f"Keep the hook under about {max_units} units.",
            )
        )

    overlong = [
        sentence
        for sentence in sentences(script or "")
        if count_units(sentence, language) > max_units
    ]
    if overlong:
        issues.append(
            ScriptIssue(
                code="long_sentence",
                severity=ScriptIssueSeverity.WARNING,
                message=f"{len(overlong)} sentence(s) exceed {max_units} units.",
                hint=f'Tighten, for example: "{overlong[0][:120]}"',
            )
        )

    if style is not None:
        lowered = body.lower()
        for phrase in style.banned_phrases:
            if phrase and phrase.lower() in lowered:
                issues.append(
                    ScriptIssue(
                        code="banned_phrase",
                        severity=ScriptIssueSeverity.WARNING,
                        message=f"Banned phrase from '{style.name}': \"{phrase}\".",
                        hint="Rewrite the line without the cliché.",
                    )
                )
        if style.cta and not any(
            style.cta.split()[0].lower() in section.text.lower() for section in sections
        ):
            issues.append(
                ScriptIssue(
                    code="missing_cta",
                    severity=ScriptIssueSeverity.INFO,
                    message="No call to action detected.",
                    hint=f"'{style.name}' expects something like: {style.cta}",
                )
            )

    sources: list[str] = []
    if research is not None:
        for source in research.sources:
            sources.extend([source.summary, *source.highlights])
        sources.extend(research.key_facts)
    run, phrase = longest_shared_run(body, sources)
    if run >= COPY_RUN_WORDS:
        issues.append(
            ScriptIssue(
                code="copy_risk",
                severity=ScriptIssueSeverity.ERROR,
                message=(
                    f'{run} consecutive words match a research source: "{phrase}".'
                ),
                hint="Paraphrase and add new meaning before approving the script.",
            )
        )
    elif sources and run >= max(4, COPY_RUN_WORDS // 2):
        issues.append(
            ScriptIssue(
                code="copy_risk_minor",
                severity=ScriptIssueSeverity.INFO,
                message=f"A {run}-word phrase closely tracks a source.",
                hint="Consider rewording to stay safely transformative.",
            )
        )
    if not sources:
        issues.append(
            ScriptIssue(
                code="no_research",
                severity=ScriptIssueSeverity.INFO,
                message="The script is not grounded in research sources.",
                hint="Run research so facts can be traced and checked.",
            )
        )

    for warning in plan.warnings:
        issues.append(
            ScriptIssue(
                code="timing",
                severity=ScriptIssueSeverity.WARNING,
                message=warning,
                hint=None,
            )
        )
    return issues


_SEVERITY_WEIGHTS = {
    ScriptIssueSeverity.ERROR: 25,
    ScriptIssueSeverity.WARNING: 8,
    ScriptIssueSeverity.INFO: 2,
}


def score_issues(issues: Iterable[ScriptIssue]) -> int:
    """Convert findings into a 0–100 readiness score."""
    score = 100
    for issue in issues:
        score -= _SEVERITY_WEIGHTS.get(issue.severity, 5)
    return max(0, score)


def analyze_script(
    script: str | None,
    *,
    language: str = "en",
    target_seconds: int = 45,
    style: ScriptStyle | None = None,
    research: ResearchBundle | None = None,
) -> ScriptAnalysis:
    """Plan + lint a script in one call."""
    plan = plan_script(
        script, language=language, target_seconds=target_seconds, style=style
    )
    issues = lint_script(
        script,
        language=language,
        target_seconds=target_seconds,
        style=style,
        research=research,
        plan=plan,
    )
    return ScriptAnalysis(plan=plan, issues=issues, score=score_issues(issues))


# --- Prompt construction -----------------------------------------------------


def style_directives(style: ScriptStyle, language: str) -> str:
    """Render the style contract as prompt bullets."""
    code = (language or "en").split("-")[0].strip().lower()
    profile = language_profile(language)
    lines = [f"- Tone: {style.tone}"]
    if style.structure:
        markers = " ".join(f"[{item}]" for item in style.structure)
        lines.append(
            f"- Follow this section order, each marker on its own line: {markers}"
        )
    if style.hook_rules:
        lines.append("- Hook rules:")
        lines.extend(f"  - {rule}" for rule in style.hook_rules)
    lines.append(
        f"- Keep every sentence under {style.sentence_max_units} {profile.unit_name}."
    )
    lines.append(f"- At most {style.max_sections} sections.")
    if style.cta:
        lines.append(f'- End with a call to action in the spirit of: "{style.cta}"')
    else:
        lines.append("- No call to action; end on the payoff.")
    if style.banned_phrases:
        lines.append(
            "- Never use these phrases: "
            + ", ".join(f'"{phrase}"' for phrase in style.banned_phrases)
        )
    note = style.language_notes.get(code)
    if note:
        lines.append(f"- Language note ({code}): {note}")
    return "\n".join(lines)


def build_script_prompt(
    *,
    topic: str,
    language: str = "vi",
    target_seconds: int = 45,
    style: ScriptStyle,
    research: ResearchBundle | None = None,
    grounding: GroundingBundle | None = None,
    reference_notes: str | None = None,
    extra_directives: Iterable[str] | None = None,
) -> str:
    """Build a contract-style narration prompt for a high-end model.

    The header lines (``Topic:``, ``Language:``, ``Target duration:`` and the
    contiguous ``Key facts:`` list) are part of the contract with the built-in
    template provider and must stay parseable.
    """
    profile = language_profile(language)
    rate = resolve_rate(language, style)
    budget_units = max(1, round(rate * target_seconds * 0.95))

    header = [
        f"Topic: {topic}",
        f"Language: {language}",
        f"Target duration: {int(target_seconds)} seconds",
        f"Style preset: {style.name} — {style.title or style.name}",
        "",
        "# ROLE",
        "You are a senior short-form showrunner and narration writer. You write",
        "scripts that hold attention on a phone screen and can be narrated",
        "verbatim by a text-to-speech engine.",
        "",
        "# TASK",
        f"Write ONE original narration script about the topic above, in "
        f"{profile.label}.",
        f"It must take about {int(target_seconds)} seconds to read aloud "
        f"(roughly {budget_units} {profile.unit_name}).",
        "",
        "# HARD CONSTRAINTS",
        style_directives(style, language),
        "- Learn facts, numbers, and framing from the reference material below.",
        "- Never reuse a sentence from the references. Do not reproduce more",
        f"  than {COPY_RUN_WORDS} consecutive words from any single source.",
        "- Invent the wording, the metaphor, and the transitions yourself.",
        "- Write only spoken narration: no stage directions, no camera notes,",
        "  no headings other than the section markers, no emoji.",
    ]
    if style.description:
        header.extend(["", "# STYLE INTENT", style.description.strip()])
    directives = [item.strip() for item in (extra_directives or []) if item.strip()]
    if directives:
        header.append("")
        header.append("# OPERATOR OVERRIDES")
        header.extend(f"- {item}" for item in directives)

    body: list[str] = ["", "# REFERENCE MATERIAL (learn from, never copy)"]
    if research is not None and research.sources:
        for source in research.sources:
            body.append(
                f"- {source.title} ({source.source_type}): {source.summary.strip()}"
            )
            for highlight in source.highlights[:2]:
                body.append(f"  - {highlight.strip()}")
    else:
        body.append("- No research has been gathered; rely on general knowledge.")
    if grounding is not None and grounding.context_text:
        body.extend(
            [
                "",
                "## Knowledge base (cite as [n] in your own words)",
                grounding.context_text.strip(),
                "",
                "- Every factual claim must be backed by one of the [n] entries",
                "  above, or by the Key facts list. If neither covers it, cut it.",
            ]
        )
    if reference_notes:
        body.extend(["", "## Reference video notes (style only, never copied)"])
        body.append(reference_notes.strip())

    if research is not None and research.key_facts:
        body.append("")
        body.append("Key facts:")
        body.extend(f"- {fact.strip()}" for fact in research.key_facts)

    body.extend(
        [
            "",
            "# OUTPUT CONTRACT",
            "Return ONLY the script. Use the section markers exactly as shown,",
            "each on its own line, with no extra commentary before or after.",
            "",
        ]
    )
    for index, marker in enumerate(style.structure):
        body.append(f"[{marker}]")
        if index == 0:
            body.append("<one or two sentences that create immediate tension>")
        elif style.cta and marker.lower() in {"cta", "outro", "closing"}:
            body.append(style.cta)
        else:
            body.append("<the narration for this beat>")
        body.append("")
    while body and not body[-1]:
        body.pop()
    return "\n".join(header + body)
