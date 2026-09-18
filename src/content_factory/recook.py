"""Content re-cook pipeline: transform any source media into a new video.

The "re-cook" workflow takes a source video/audio/document, lets an AI agent
read it (transcription / text extraction), then produces a brand-new script
that keeps the factual spine but re-words it, re-times it, swaps the hook and
call-to-action, and optionally changes the soundtrack. A new project is created
so the normal two-gate human approval flow still applies.
"""

from __future__ import annotations

import re

from .config import Settings
from .media import MediaLibrary
from .models import (
    MediaItem,
    Project,
    ProjectCreate,
    ReCookMode,
    ReCookRequest,
    ReCookResult,
    utcnow,
)
from .store import Store

_SECTION_LABELS = ["Hook", "Context", "Turn", "Payoff", "CTA"]

# Rough speaking rate: ~14 chars/second for English narration.
_CHARS_PER_SECOND = 14.0


def _sentences(text: str) -> list[str]:
    """Split text into trimmed, non-empty sentences."""
    parts = re.split(r"(?<=[.!?])\s+", text.replace("\n", " "))
    return [p.strip() for p in parts if p.strip()]


def _estimate_seconds(text: str) -> int:
    return max(1, round(len(text) / _CHARS_PER_SECOND))


_SYNONYMS = {
    "battle": "conflict",
    "war": "conflict",
    "lasted": "ran",
    "began": "started",
    "bloodiest": "most brutal",
    "huge": "major",
    "important": "significant",
    "ordinary": "common",
    "terrible": "harsh",
    "conditions": "circumstances",
    "symbol": "emblem",
    "studied": "examined",
    "lessons": "insights",
    "turning point": "decisive shift",
    "surrounded": "encircled",
    "surrender": "capitulation",
    "marked": "signaled",
    "played": "had",
    "role": "part",
    "outcome": "result",
    "endured": "faced",
    "city": "urban centre",
    "historians": "scholars",
    "today": "nowadays",
    "became": "turned into",
    "resistance": "defiance",
    "logistics": "supply lines",
    "winter": "the cold season",
    "troops": "forces",
    "soldiers": "fighting men",
    "attack": "assault",
    "defense": "defence",
    "victory": "win",
    "defeat": "loss",
    "leader": "commander",
    "army": "forces",
    "people": "population",
    "years": "years on end",
}


def _reword(sentence: str) -> str:
    """Paraphrase a sentence so the cut is not a verbatim copy of the source.

    Combines phrase-level compression, pattern-based restructuring, and a
    synonym map. This is a deterministic stand-in for a strong LLM re-writer;
    when a real provider is configured the pipeline can use it instead.
    """
    out = " " + sentence.strip() + " "

    # Pattern: "The <X> lasted from <A> to <B>." -> "Spanning <A> to <B>, <X> ran."
    m = re.match(
        r"\s*(?:The\s+|A\s+|An\s+)?(.+?)\s+lasted\s+from\s+(.+?)\s+to\s+(.+?)\.?\s*$",
        out,
        re.IGNORECASE,
    )
    if m:
        subject = m.group(1).strip()
        a, b = m.group(2).strip(), m.group(3).strip()
        out = f" Spanning {a} to {b}, {subject} ran on. "

    # Pattern: "It was one of the <X>." -> "Few <X> matched it."
    m = re.match(r"\s*It\s+was\s+one\s+of\s+the\s+(.+?)\.?\s*$", out, re.IGNORECASE)
    if m:
        out = f" Few {m.group(1).strip()} ever matched it. "

    # Pattern: "<X> became a <Y>." -> "<X> grew into a <Y>."
    m = re.match(r"\s*(.+?)\s+became\s+a\s+(.+?)\.?\s*$", out, re.IGNORECASE)
    if m:
        out = f" {m.group(1).strip()} grew into a {m.group(2).strip()}. "

    # Phrase-level compression.
    for old, new in [
        (" is going to ", " will "),
        (" are going to ", " will "),
        (" in order to ", " to "),
        (" a lot of ", " plenty of "),
        (" due to the fact that ", " because "),
        (" at this point in time ", " now "),
        (" at the end of the day ", " ultimately "),
        (" it is important to note that ", " note that "),
        (" the fact that ", " that "),
    ]:
        out = out.replace(old, new)

    # Word-level synonyms (whole-word, case-aware).
    words = out.split(" ")
    swapped: list[str] = []
    for word in words:
        lowered = word.lower().rstrip(".,;:!?")
        punct = word[len(lowered) :]
        replacement = _SYNONYMS.get(lowered)
        if replacement is not None:
            if word[:1].isupper():
                replacement = replacement[:1].upper() + replacement[1:]
            swapped.append(replacement + punct)
        else:
            swapped.append(word)
    out = " ".join(swapped)

    # Collapse whitespace and strip filler words.
    out = re.sub(r"\s+", " ", out).strip()
    for filler in [
        " basically ",
        " actually ",
        " you know ",
        " kind of ",
        " sort of ",
        " really ",
        " just ",
    ]:
        out = out.replace(filler, " ")
    out = re.sub(r"\s+", " ", out).strip()
    return out


def _pick_sentences(
    sentences: list[str], target_seconds: int, mode: ReCookMode
) -> list[str]:
    """Select/trim sentences to approximate the target narration length."""
    if not sentences:
        return ["This story deserves a closer look."]
    budget = target_seconds * _CHARS_PER_SECOND
    chosen: list[str] = []
    used = 0
    # Prefer the most information-dense sentences first.
    if mode == ReCookMode.CONDENSE:
        ordered = sorted(sentences, key=len, reverse=True)
    else:
        ordered = sentences
    for sentence in ordered:
        reworded = _reword(sentence)
        if used + len(reworded) > budget and chosen:
            if mode == ReCookMode.EXPAND:
                continue
            break
        chosen.append(reworded)
        used += len(reworded)
        if used >= budget:
            break
    if not chosen:
        chosen = [_reword(sentences[0])[: int(budget)] or _reword(sentences[0])]
    return chosen


def build_recooked_script(
    transcript: str,
    new_title: str,
    target_seconds: int,
    mode: ReCookMode,
    language: str = "en",
) -> str:
    """Turn a source transcript into a fresh, re-worded narration script."""
    sentences = _sentences(transcript)
    body = _pick_sentences(sentences, target_seconds, mode)

    # Build a new hook from the title/topic, and a fresh CTA.
    topic = new_title.strip() or "this story"
    hook = (
        f"What most people never learn about {topic} changes everything."
        if body
        else f"There is more to {topic} than meets the eye."
    )
    context = body[0] if body else f"The details behind {topic} are worth knowing."
    turn = body[1] if len(body) > 1 else "Look closer and the pattern becomes clear."
    payoff = body[-1] if body else "That is the real story hiding in plain sight."
    middle = body[2:-1] if len(body) > 3 else []

    lines = [
        "[Hook]",
        hook,
        "",
        "[Context]",
        context,
        "",
    ]
    if middle:
        lines.extend(["[Turn]", *middle, ""])
    else:
        lines.extend(["[Turn]", turn, ""])
    lines.extend(
        [
            "[Payoff]",
            payoff,
            "",
            "[CTA]",
            "Follow for more stories like this.",
        ]
    )
    return "\n".join(lines)


class RecookPipeline:
    """Coordinates a re-cook run against the media library and project store."""

    def __init__(self, settings: Settings, media: MediaLibrary) -> None:
        self._settings = settings
        self._media = media

    def prepare_source(self, media_id: str) -> MediaItem:
        """Ensure the source item is readable by an AI agent."""
        item = self._media.require(media_id)
        if item.kind in ("video", "audio") and not item.transcription:
            return self._media.transcribe(media_id, language=item.language or "en")
        if item.kind == "document" and not item.text_content:
            return self._media.extract_text(media_id)
        return item

    def _source_text(self, item: MediaItem) -> str:
        if item.transcription:
            return item.transcription
        if item.text_content:
            return item.text_content
        return item.filename

    def build_script(self, item: MediaItem, request: ReCookRequest) -> str:
        source = self._source_text(item)
        return build_recooked_script(
            source,
            request.new_title,
            request.target_seconds,
            request.mode,
            request.language,
        )

    def create_project(
        self,
        item: MediaItem,
        request: ReCookRequest,
        script: str,
        store: Store,
    ) -> Project:
        """Create a new project and set the re-cooked script on it."""
        title = request.new_title.strip() or f"Re-cooked {item.filename}"
        topic = title
        project = store.create(
            ProjectCreate(
                name=title,
                topic=topic,
                target_language=request.language,
                duration_target_seconds=request.target_seconds,
            )
        )
        project.script = script
        project.script_style = request.script_style
        project.source_rights_confirmed = False
        project.source_media_id = item.id
        project.error = None
        # Move into script_review so a human can confirm rights and approve.
        from .state import ProjectStatus, assert_transition

        assert_transition(project.status, ProjectStatus.SCRIPT_REVIEW)
        project.status = ProjectStatus.SCRIPT_REVIEW
        store.save(project)
        return project

    def run(self, media_id: str, request: ReCookRequest, store: Store) -> ReCookResult:
        """Run the full re-cook: read -> re-word -> new project."""
        item = self.prepare_source(media_id)
        script = self.build_script(item, request)
        project = self.create_project(item, request, script, store)
        return ReCookResult(
            media_id=media_id,
            project_id=project.id,
            project_name=project.name,
            new_title=request.new_title.strip() or f"Re-cooked {item.filename}",
            mode=request.mode,
            source_transcript=self._source_text(item),
            script=script,
            estimated_seconds=_estimate_seconds(script),
            status="script_review",
            created_at=utcnow(),
        )
