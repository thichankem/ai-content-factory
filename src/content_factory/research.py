"""Research engine: gathers reference sources and key facts for a topic.

The engine scores a curated reference library against the topic keywords,
selects the most relevant sources, and always appends a topic-specific field
note so every research pass yields usable material. Highlights and key facts
give the script providers concrete grounding.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .models import (
    FactClaim,
    FactConfidence,
    FactReconciliationReport,
    HistoricalEvent,
    ResearchBundle,
    ResearchSource,
    StructuredTimeline,
    utcnow,
)
from .text import slugify as _slug
from .text import tokenize


@dataclass(frozen=True)
class SeedSource:
    """A reference document in the curated library."""

    title: str
    url: str
    source_type: str
    summary: str
    keywords: tuple[str, ...]
    highlights: tuple[str, ...] = field(default_factory=tuple)


_SEED_SOURCES: tuple[SeedSource, ...] = (
    SeedSource(
        title="The Science of Attention: Why Short Videos Hook Us",
        url="https://reference.local/science-of-attention",
        source_type="article",
        summary=(
            "Attention is a scarce resource; the first three seconds decide "
            "whether a viewer stays. Pattern interrupts and motion win the "
            "scroll."
        ),
        keywords=("attention", "hook", "video", "short", "retention", "scroll"),
        highlights=(
            "Viewers decide to stay or swipe within the first three seconds.",
            "Sudden movement, a question, or an unresolved image interrupts scrolling.",
            "Short videos win by compressing a payoff into the first ten percent of",
            "runtime.",
        ),
    ),
    SeedSource(
        title="Three-Act Structure for Micro-Stories",
        url="https://reference.local/three-act-micro-stories",
        source_type="article",
        summary=(
            "Even a 45-second story needs a setup, a turn, and a payoff. "
            "Micro-stories compress the arc without dropping the tension."
        ),
        keywords=("structure", "story", "arc", "narrative", "act", "tension"),
        highlights=(
            "A micro-story is a promise in the first line and a delivery in the last.",
            "The turn introduces the detail that reframes everything before it.",
            "Payoffs land harder when the setup feels ordinary.",
        ),
    ),
    SeedSource(
        title="Chronobiology: How Morning Light Resets Circadian Rhythms",
        url="https://reference.local/morning-light-circadian",
        source_type="paper",
        summary=(
            "Morning light is the strongest zeitgeber for the circadian clock. "
            "Early exposure shifts alertness, mood, and sleep timing."
        ),
        keywords=("morning", "light", "circadian", "sunrise", "sleep", "alertness"),
        highlights=(
            "Bright light in the first hour after waking advances the circadian phase.",
            "Light intensity, not just presence, drives the biological response.",
            "Consistent morning exposure stabilizes energy across the day.",
        ),
    ),
    SeedSource(
        title="The Psychology of Habits: Cue, Routine, Reward",
        url="https://reference.local/psychology-of-habits",
        source_type="book",
        summary=(
            "Habits form through a loop of cue, routine, and reward. "
            "Changing the cue is easier than fighting the routine."
        ),
        keywords=("habit", "routine", "cue", "reward", "behavior", "loop"),
        highlights=(
            "Every habit is a loop: cue, routine, reward.",
            "Small environmental cues trigger routines without conscious thought.",
            "Identity-based habits stick longer than outcome-based ones.",
        ),
    ),
    SeedSource(
        title="Urban Design and the Rhythm of the City",
        url="https://reference.local/urban-design-rhythm",
        source_type="article",
        summary=(
            "Cities breathe on schedules: deliveries, markets, commuters. "
            "Observing those rhythms reveals the hidden life of a place."
        ),
        keywords=("city", "urban", "street", "neighborhood", "market", "commute"),
        highlights=(
            "A city has a pulse: the same corner looks different at 5am and noon.",
            "Infrastructure is choreography — lights, doors, and trucks follow a",
            "script.",
            "Quiet hours reveal who actually runs a place.",
        ),
    ),
    SeedSource(
        title="Color Psychology in Visual Storytelling",
        url="https://reference.local/color-psychology",
        source_type="article",
        summary=(
            "Palette shapes emotional reading before the story begins. "
            "Warm and cool tones set temperature, mood, and genre expectations."
        ),
        keywords=("color", "palette", "visual", "emotion", "tone", "mood"),
        highlights=(
            "Color sets emotional temperature before a single word is spoken.",
            "Contrast directs the eye to the subject of the frame.",
            "A consistent palette makes a sequence feel intentional.",
        ),
    ),
    SeedSource(
        title="Sound Design for Vertical Video",
        url="https://reference.local/sound-design-vertical",
        source_type="article",
        summary=(
            "Audio carries half the emotion in short video. Voice, ambience, "
            "and music must survive phone speakers."
        ),
        keywords=("sound", "music", "audio", "voice", "ambience", "speaker"),
        highlights=(
            "Phone speakers crush bass; design for midrange clarity.",
            "Ambient sound sells realism even when the image is stylized.",
            "Music tells the viewer how to feel before the narrator speaks.",
        ),
    ),
    SeedSource(
        title="Retention Metrics: Watch Time and Completion Rate",
        url="https://reference.local/retention-metrics",
        source_type="report",
        summary=(
            "Completion rate and average watch time measure whether a story "
            "holds. Drops cluster at predictable points in the arc."
        ),
        keywords=(
            "retention",
            "watch time",
            "analytics",
            "metric",
            "drop",
            "completion",
        ),
        highlights=(
            "Most viewers drop in the first five seconds; the hook is the funnel.",
            "Watch time rewards pacing that pays off promises quickly.",
            "Completion spikes when the payoff mirrors the opening question.",
        ),
    ),
    SeedSource(
        title="Originality in AI-Assisted Content: Copyright and Fair Use",
        url="https://reference.local/originality-copyright",
        source_type="guide",
        summary=(
            "AI may learn from sources but must not reproduce them verbatim. "
            "Confirm rights before production; transform, don't copy."
        ),
        keywords=(
            "copyright",
            "original",
            "fair use",
            "rights",
            "license",
            "transform",
        ),
        highlights=(
            "Learning a topic is not the same as copying an expression of it.",
            "Transformative use hinges on adding new meaning, not repackaging.",
            "Confirm source rights before any production step.",
        ),
    ),
    SeedSource(
        title="Voice and Pacing in Narration",
        url="https://reference.local/voice-and-pacing",
        source_type="article",
        summary=(
            "Narration pacing controls comprehension and emotion. Short "
            "sentences build urgency; pauses create emphasis."
        ),
        keywords=("voice", "narration", "pacing", "tone", "script", "pause"),
        highlights=(
            "Short sentences read faster and feel more urgent.",
            "A well-placed pause makes the next line land harder.",
            "Match sentence rhythm to the emotional beat of the scene.",
        ),
    ),
    SeedSource(
        title="The Hook Formula: Open Loops and Curiosity Gaps",
        url="https://reference.local/hook-formula",
        source_type="article",
        summary=(
            "Hooks open a loop the brain wants closed. Questions, stakes, and "
            "unfinished ideas pull viewers forward."
        ),
        keywords=(
            "hook",
            "curiosity",
            "open loop",
            "cliffhanger",
            "question",
            "stakes",
        ),
        highlights=(
            "An open loop is a question the brain insists on answering.",
            "Concrete stakes beat vague promises in the first line.",
            "The best hooks promise a transformation, not just information.",
        ),
    ),
    SeedSource(
        title="Creator Economy Trends 2026",
        url="https://reference.local/creator-economy-2026",
        source_type="report",
        summary=(
            "Authenticity, niche depth, and serialized formats outperform "
            "polished one-offs. Audiences follow voices, not channels."
        ),
        keywords=("creator", "trend", "platform", "audience", "niche", "authentic"),
        highlights=(
            "Niche creators outgrow generalists by owning one topic deeply.",
            "Serialized formats turn viewers into subscribers.",
            "Audiences reward consistency of voice over production gloss.",
        ),
    ),
    SeedSource(
        title="Visual Hierarchy: Guiding the Eye on Screen",
        url="https://reference.local/visual-hierarchy",
        source_type="article",
        summary=(
            "Composition, contrast, and motion guide the viewer's eye. "
            "Hierarchy decides what is seen first and remembered longest."
        ),
        keywords=("visual", "hierarchy", "composition", "frame", "contrast", "eye"),
        highlights=(
            "The eye lands on the highest-contrast element first.",
            "Rule-of-thirds placement reads as intentional and calm.",
            "Motion pulls attention away from static subjects.",
        ),
    ),
    SeedSource(
        title="Emotion Drives Sharing: The Psychology of Virality",
        url="https://reference.local/emotion-virality",
        source_type="paper",
        summary=(
            "High-arousal emotions — awe, amusement, anger — drive sharing. "
            "Content that makes someone feel something gets passed on."
        ),
        keywords=("emotion", "virality", "share", "psychology", "arousal", "awe"),
        highlights=(
            "High-arousal emotions measurably increase sharing.",
            "Surprise followed by clarity is the most shared emotional shape.",
            "People share to express identity, not just to inform.",
        ),
    ),
)


def _tokenize(text: str) -> set[str]:
    """Score tokenizer policy: every alphanumeric word, order-insensitive."""
    return set(tokenize(text))


class ResearchEngine:
    """Scores the reference library and assembles a research bundle."""

    def __init__(self, max_sources: int = 6) -> None:
        self._max_sources = max(1, max_sources)

    def research(self, topic: str) -> ResearchBundle:
        tokens = _tokenize(topic)
        scored = sorted(
            ((source, self._score(source, tokens)) for source in _SEED_SOURCES),
            key=lambda item: item[1],
            reverse=True,
        )
        budget = max(1, self._max_sources - 1)
        selected = [source for source, score in scored if score > 0][:budget]
        if len(selected) < budget and scored:
            for source, _ in scored:
                if source not in selected:
                    selected.append(source)
                if len(selected) >= budget:
                    break
        selected.append(self._synthetic_source(topic))

        sources = [
            self._to_model(source, relevance)
            for source, relevance in self._rank(selected)
        ]
        key_facts = self._key_facts(sources)
        notes = (
            f"Collected {len(sources)} sources for '{topic}'. "
            "Review the highlights below; the draft is grounded in these facts."
        )
        return ResearchBundle(
            sources=sources,
            key_facts=key_facts,
            notes=notes,
            generated_at=utcnow(),
        )

    def _score(self, source: SeedSource, tokens: set[str]) -> int:
        keyword_overlap = set(source.keywords) & tokens
        title_overlap = _tokenize(source.title) & tokens
        return len(keyword_overlap) + 2 * len(title_overlap)

    def _rank(self, sources: list[SeedSource]) -> list[tuple[SeedSource, float]]:
        ranked: list[tuple[SeedSource, float]] = []
        for index, source in enumerate(sources):
            relevance = max(0.0, 1.0 - index / max(1, len(sources)))
            ranked.append((source, round(relevance, 2)))
        return ranked

    def _to_model(self, source: SeedSource, relevance: float) -> ResearchSource:
        return ResearchSource(
            id=_slug(source.title),
            title=source.title,
            url=source.url,
            source_type=source.source_type,
            summary=source.summary,
            highlights=list(source.highlights),
            relevance=relevance,
        )

    def _synthetic_source(self, topic: str) -> SeedSource:
        """Always-on field note so every research pass yields usable material."""
        return SeedSource(
            title=f"Field note: {topic}",
            url=f"https://notes.local/topics/{_slug(topic)}",
            source_type="note",
            summary=(
                f"A working note synthesizing observations about '{topic}' "
                "for the narration script."
            ),
            keywords=tuple(_tokenize(topic)),
            highlights=(
                (
                    f"'{topic}' rewards a closer look; the details most people "
                    "miss carry the story."
                ),
                (
                    f"Viewers remember one vivid detail about {topic} more than "
                    "a list of facts."
                ),
                (
                    f"The strongest scripts about {topic} open with tension and "
                    "pay it off with clarity."
                ),
            ),
        )

    def _key_facts(self, sources: list[ResearchSource]) -> list[str]:
        facts: list[str] = []
        for source in sources:
            if source.highlights:
                facts.append(f"{source.title}: {source.highlights[0]}")
        return facts[:8]


# --- Structured Timeline & Fact Reconciliation Helpers ------------------------


_TIME_STAMP_PATTERNS = [
    re.compile(r"\b(\d{1,2}:\d{2}(?:\s*(?:AM|PM|am|pm))?)\b"),
    re.compile(
        r"\b(?:Ngày|Date)?\s*(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:Năm|Year)\s*(\d{4})\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:Phút|Minute)\s*(\d{1,3})\b",
        re.IGNORECASE,
    ),
]

_CLIMAX_KEYWORDS = frozenset(
    {
        "va chạm",
        "chìm",
        "nổ",
        "sập",
        "cháy",
        "tử vong",
        "tai nạn",
        "thảm họa",
        "collision",
        "impact",
        "sank",
        "sinking",
        "exploded",
        "explosion",
        "collapse",
        "breach",
    }
)


def extract_structured_timeline(text: str, topic: str = "") -> StructuredTimeline:
    """Extract chronological events from raw research text or script."""
    events: list[HistoricalEvent] = []
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    if not lines and topic:
        lines = [topic]

    current_offset = 0
    climax_idx: int | None = None

    for idx, line in enumerate(lines):
        ts_match = None
        for pattern in _TIME_STAMP_PATTERNS:
            found = pattern.search(line)
            if found:
                ts_match = found.group(1)
                break

        timestamp = ts_match or f"T+{idx * 3}m"

        # Check for casualty mentions e.g. "1,517 người", "1500 victims"
        cas_match = re.search(
            r"(\d[\d,.]*)\s*(?:người|nạn nhân|victims|casualties)",
            line,
            re.IGNORECASE,
        )
        casualties = None
        if cas_match:
            try:
                casualties = int(cas_match.group(1).replace(",", "").replace(".", ""))
            except ValueError:
                casualties = None

        is_climax = any(k in line.lower() for k in _CLIMAX_KEYWORDS)
        if is_climax and climax_idx is None:
            climax_idx = len(events)

        title = line[:60] if len(line) <= 60 else line[:57] + "..."
        events.append(
            HistoricalEvent(
                timestamp=timestamp,
                title=title,
                description=line,
                casualties=casualties,
                is_climax=is_climax,
                time_offset_seconds=current_offset,
            )
        )
        current_offset += 60  # Default 60s per milestone

    if not events:
        events.append(
            HistoricalEvent(
                timestamp="00:00",
                title=topic or "Bắt đầu sự kiện",
                description="Bắt đầu diễn tiến lịch sử",
                is_climax=False,
                time_offset_seconds=0,
            )
        )

    cas_list = [e.casualties for e in events if e.casualties is not None]
    total_casualties = sum(cas_list) if cas_list else None

    return StructuredTimeline(
        topic=topic or "Dòng thời gian sự kiện",
        events=events,
        total_span=f"{len(events)} mốc sự kiện",
        climax_event_index=climax_idx,
        total_casualties=total_casualties,
    )


def reconcile_facts(
    claims: list[FactClaim] | None = None,
    text: str = "",
    sources: list[ResearchSource] | None = None,
) -> FactReconciliationReport:
    """Reconcile sensitive statistics (casualties, dates, damage) across sources."""
    claims_list: list[FactClaim] = list(claims or [])

    # Auto-extract claims from sources if none provided
    src_list = sources or []
    casualty_numbers: dict[str, list[str]] = {}

    for src in src_list:
        combined = f"{src.title} {src.summary} {' '.join(src.highlights)}"
        matches = re.findall(
            r"(\d[\d,.]*)\s*(?:người|nạn nhân|victims|casualties|chết|thiệt mạng)",
            combined,
            re.IGNORECASE,
        )
        for m in matches:
            clean_num = m.replace(",", "").replace(".", "")
            if clean_num.isdigit() and int(clean_num) > 0:
                casualty_numbers.setdefault(clean_num, []).append(src.title)

    if not claims_list and casualty_numbers:
        if len(casualty_numbers) == 1:
            val, srcs = next(iter(casualty_numbers.items()))
            conf = (
                FactConfidence.VERIFIED if len(srcs) >= 2 else FactConfidence.ESTIMATED
            )
            claims_list.append(
                FactClaim(
                    claim_type="casualties",
                    value=f"{val} người",
                    confidence=conf,
                    sources=srcs,
                    discrepancy_notes="Số liệu đồng thuận trên các nguồn nghiên cứu.",
                )
            )
        else:
            # Discrepancy found
            all_srcs: list[str] = []
            values_str = ", ".join(
                f"{v} ({len(s)} nguồn)" for v, s in casualty_numbers.items()
            )
            for s in casualty_numbers.values():
                all_srcs.extend(s)
            claims_list.append(
                FactClaim(
                    claim_type="casualties",
                    value=values_str,
                    confidence=FactConfidence.DISPUTED,
                    sources=list(set(all_srcs)),
                    discrepancy_notes=(
                        "Phát hiện chênh lệch số liệu thương vong giữa các nguồn. "
                        "Khuyến nghị nêu rõ trong kịch bản: 'Theo các ước tính...'"
                    ),
                )
            )

    verified = sum(1 for c in claims_list if c.confidence == FactConfidence.VERIFIED)
    disputed = sum(1 for c in claims_list if c.confidence == FactConfidence.DISPUTED)

    overall = "verified"
    if disputed > 0:
        overall = "disputed"
    elif not claims_list:
        overall = "unverified"

    summary = (
        f"Đối soát xong: {verified} số liệu xác thực, "
        f"{disputed} số liệu có tranh cãi/chênh lệch."
    )

    return FactReconciliationReport(
        topic=src_list[0].title if src_list else "Đối soát dữ liệu lịch sử",
        claims=claims_list,
        verified_count=verified,
        disputed_count=disputed,
        overall_confidence=overall,
        audit_summary=summary,
    )
