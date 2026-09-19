from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from .common import TwinSpelling
from .timeline import VideoProject

#: The call kinds :class:`~content_factory.cost_guard.CostGuard` has unit costs
#: for. A plan that names anything else cannot be priced, and pricing it as
#: $0.00 would hide the omission.
PRICED_CALL_KINDS: tuple[str, ...] = (
    "vision",
    "audio_llm",
    "tts",
    "stt",
    "embedding",
)


class PlatformCheckRequest(BaseModel):
    platform: str
    duration_seconds: float | None = None
    aspect_ratio: str = ""
    words: int = 0
    text: str = ""


class BrandCheckRequest(BaseModel):
    dominant_colors: list[str] = Field(default_factory=list)
    fonts_used: list[str] = Field(default_factory=list)
    has_logo: bool = False
    palette: list[str] = Field(default_factory=list)
    fonts: list[str] = Field(default_factory=list)
    logo_fingerprints: list[str] = Field(default_factory=list)


class CopyrightCheckRequest(BaseModel):
    """A fingerprint to clear, or a batch of asset ids to clear at once.

    ``fingerprint`` is the canonical single-check field. ``asset_ids`` is the
    batch spelling the web clients send: each id is treated as a fingerprint and
    reported on individually, so a UI can tick a list of assets without knowing
    how fingerprints are computed.
    """

    fingerprint: str | None = None
    asset_ids: list[str] = Field(default_factory=list)
    protected: list[str] = Field(default_factory=list)

    @property
    def candidates(self) -> list[str]:
        """Every fingerprint to check, in order, without duplicates."""
        seen: list[str] = []
        for value in (self.fingerprint, *self.asset_ids):
            if value and value not in seen:
                seen.append(value)
        return seen

    # There is deliberately no "at least one candidate" rule here. Clearing an
    # empty batch is a legitimate request — the studio ticks a list of assets and
    # the operator may have ticked none — and the honest answer is that nothing
    # was checked, so nothing was blocked. Rejecting it made a UI button fail for
    # a state the UI itself can produce. Callers that passed a malformed body get
    # an explicit `checked: 0` back instead of a 422.


class AuditRecordRequest(BaseModel):
    actor: str = Field(min_length=1)
    action: str = Field(min_length=1)
    project_id: str | None = None
    media_id: str | None = None
    prompt: str | None = None
    detail: str | None = None


class CostCheckRequest(BaseModel):
    """A plan of model calls to price.

    ``calls`` is the canonical field the CLI, the pipeline and the agent tools
    use; ``estimated_usage`` is what the studio sends. Both are accepted and the
    two are merged, because a client that sends the spelling we do not read gets
    a silent $0.00 estimate rather than an error — the most expensive kind of
    contract drift.

    Either field also accepts the shape an *agent* writes when it describes a
    plan call by call (``[{"kind": "tts", "model": "...", "count": 2}]``), which
    is aggregated into the same counts. A call whose kind cannot be priced is
    rejected instead of priced at zero: an estimate that quietly omits half a
    plan is worse than no estimate.
    """

    calls: dict[str, int] | list[dict[str, Any]] = Field(default_factory=dict)
    estimated_usage: dict[str, int] | list[dict[str, Any]] = Field(default_factory=dict)

    @field_validator("calls", "estimated_usage", mode="before")
    @classmethod
    def _normalize_usage(cls, value: Any) -> Any:
        """Turn a list of call descriptors into counts, or leave a mapping alone.

        The count-map spelling deliberately tolerates keys the guard has no unit
        cost for (a client that adds a new kind is not blocked, and the estimate
        simply omits it). A *list* cannot make that trade: it carries no counts
        at all, so an entry without a recognizable kind would price the whole
        plan at $0.00 and look like a successful answer. Such a list is refused
        with the accepted kinds named instead.
        """
        if not isinstance(value, list):
            return value
        counts: dict[str, int] = {}
        unpriced: list[str] = []
        for entry in value:
            if not isinstance(entry, dict):
                raise ValueError(
                    "each entry must be an object like {'kind': 'tts', 'count': 2}"
                )
            kind = str(entry.get("kind") or entry.get("type") or "").strip().lower()
            if kind not in PRICED_CALL_KINDS:
                unpriced.append(kind or repr(entry))
                continue
            counts[kind] = counts.get(kind, 0) + max(1, int(entry.get("count", 1)))
        if unpriced and not counts:
            raise ValueError(
                f"cannot price these call(s): {unpriced}; priced kinds are "
                f"{list(PRICED_CALL_KINDS)}. Send a count map instead, e.g. "
                '{"tts": 2, "vision": 1}.'
            )
        return counts

    @property
    def usage(self) -> dict[str, int]:
        """Every priced call, whichever field carried it.

        Both fields are normalized to counts during validation, so the list
        spelling is already gone by the time this runs; the isinstance guard is
        the type checker's view of that fact.
        """
        merged: dict[str, int] = {}
        for source in (self.estimated_usage, self.calls):
            if isinstance(source, dict):
                merged.update(source)
        return merged


class ViralityRequest(TwinSpelling):
    """A script to score, spelled either way by its two kinds of caller.

    ``script`` is the canonical field the CLI, the pipeline and the agent tools
    use; ``script_text`` is what both web clients send. See :class:`TwinSpelling`
    for the rule and why it is shared rather than repeated.
    """

    PRIMARY = "script"
    ALIAS = "script_text"

    script: str | None = None
    script_text: str | None = None
    topic: str | None = None
    duration_seconds: float | None = None
    hook: str | None = None

    @property
    def text(self) -> str:
        """The script body, whichever field carried it."""
        return self.resolved


class DuckRequest(BaseModel):
    music_media_id: str
    voice_media_id: str
    out: str | None = None


class ThumbnailRequest(BaseModel):
    """What to draw thumbnail candidates from.

    The source is resolved in order: an explicit ``media_id``, then a
    ``media_path`` on disk (what the web clients can supply from a preview), then
    ``project_id``'s own source media, and finally the most recently uploaded
    video asset. The last two exist so the UI can ask for thumbnails while the
    operator is looking at a project without first having to know a media id; a
    request that resolves to nothing returns no candidates rather than a 422.
    """

    media_id: str | None = None
    media_path: str | None = None
    project_id: str | None = None
    topic: str = ""
    style: str = ""
    top_k: int = Field(default=3, ge=1, le=10)
    count: int | None = Field(default=None, ge=1, le=10)
    overlays: list[str] = Field(default_factory=list)

    @property
    def limit(self) -> int:
        """How many candidates to draw: ``count`` (client spelling) or ``top_k``."""
        return self.count or self.top_k


class DedupRequest(BaseModel):
    """Which media to scan for near-duplicates.

    An omitted or empty ``media_ids`` means "scan the whole library", which is
    what the studio's one-click cleanup sends: it has no ids to hand over, it
    just wants the library swept. Requiring a non-empty list made that button
    422 while the legacy dashboard, which does pass ids, kept working.
    """

    media_ids: list[str] = Field(default_factory=list)


class TimelineCommandRequest(TwinSpelling):
    """A natural-language editing instruction and the timeline to apply it to.

    ``text`` is the canonical field the CLI, the MCP server and the agent tools
    use; ``command`` is what the studio's command bar sends. An instruction that
    is silently dropped is a command that appears to work and does nothing, which
    is why this requires one rather than defaulting to empty.
    """

    PRIMARY = "text"
    ALIAS = "command"

    project: VideoProject
    text: str | None = None
    command: str | None = None

    @property
    def instruction(self) -> str:
        """The instruction, whichever field carried it."""
        return self.resolved


class SimplifySubtitlesRequest(BaseModel):
    captions: list[str] = Field(min_length=1)
    level: str = "basic"
