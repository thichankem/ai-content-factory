"""Historical facts, sensitivity audits and map/infographic specs."""

from __future__ import annotations

import enum

from pydantic import BaseModel, Field

# --- History / Disaster / Accident Niche Models -----------------------------


class HistoricalEvent(BaseModel):
    """One discrete event in a disaster or historical timeline."""

    timestamp: str  # e.g. "1912-04-14 23:40" or "05:30"
    title: str
    description: str
    location: str | None = None
    casualties: int | None = None
    source: str | None = None
    is_climax: bool = False
    time_offset_seconds: int | None = None


class StructuredTimeline(BaseModel):
    """Chronological sequence of events parsed from research or script."""

    topic: str
    events: list[HistoricalEvent] = Field(default_factory=list)
    total_span: str | None = None
    climax_event_index: int | None = None
    total_casualties: int | None = None


class FactConfidence(enum.StrEnum):
    """Confidence tag for sensitive disaster/historical facts."""

    VERIFIED = "verified"  # Confirmed across >=2 independent sources
    DISPUTED = "disputed"  # Multiple sources give conflicting values
    ESTIMATED = "estimated"  # Approximation or witness estimate
    UNVERIFIED = "unverified"  # Only 1 unverified source


class FactClaim(BaseModel):
    """A specific sensitive claim (casualties, date, cause, loss)."""

    claim_type: str  # e.g. "casualties", "date", "cause", "financial_loss"
    value: str
    confidence: FactConfidence = FactConfidence.VERIFIED
    sources: list[str] = Field(default_factory=list)
    discrepancy_notes: str = ""


class FactReconciliationReport(BaseModel):
    """Multi-source reconciliation audit report."""

    topic: str
    claims: list[FactClaim] = Field(default_factory=list)
    verified_count: int = 0
    disputed_count: int = 0
    overall_confidence: str = "verified"
    audit_summary: str = ""


class FactReconcileRequest(BaseModel):
    """Payload for triggering a multi-source fact reconciliation pass."""

    claims: list[FactClaim] = Field(default_factory=list)


class SensitivitySeverity(enum.StrEnum):
    """Severity of an ethical or platform compliance issue."""

    CRITICAL = "critical"  # Direct violation, high demonetization risk
    WARNING = "warning"  # Sensationalist wording, unverified claim
    ADVISORY = "advisory"  # Recommendation for respectful framing


class SensitivityFinding(BaseModel):
    """One detected sensitivity or platform policy issue."""

    category: str  # "graphic_violence", "victim_respect", "unverified_conspiracy"
    severity: SensitivitySeverity = SensitivitySeverity.WARNING
    snippet: str
    message: str
    suggestion: str


class SensitivityAuditReport(BaseModel):
    """Ethical & monetization safety review report."""

    safety_score: int = Field(ge=0, le=100)  # 0 to 100
    is_safe_for_monetization: bool = True
    findings: list[SensitivityFinding] = Field(default_factory=list)
    disclaimer_required: bool = False
    recommended_disclaimer: str | None = None


class OnThisDayEvent(BaseModel):
    """A historical event or disaster anniversary for evergreen content."""

    day: int = Field(ge=1, le=31)
    month: int = Field(ge=1, le=12)
    year: int
    title: str
    category: str = "disaster"  # disaster, maritime, aviation, seismic, history
    summary: str
    casualties_estimate: str | None = None
    suggested_angle: str = ""
    keywords: list[str] = Field(default_factory=list)


class MapRoutePoint(BaseModel):
    """A geographical waypoint in a disaster path."""

    label: str
    x: float  # Normalized 0..100
    y: float  # Normalized 0..100
    timestamp: str | None = None
    note: str | None = None


class MapRouteSpec(BaseModel):
    """Specification to generate procedural SVG route maps."""

    title: str
    map_type: str = "nautical"  # nautical, aviation, earthquake, hurricane
    points: list[MapRoutePoint] = Field(default_factory=list)
    show_danger_zone: bool = True
    danger_label: str = "Point of Impact / Sinking"
    danger_x: float = 50.0
    danger_y: float = 50.0


class InfographicSpec(BaseModel):
    """Specification to generate SVG comparison infographics."""

    title: str
    subtitle: str = ""
    chart_type: str = "bar"  # bar, timeline_gauge, scale
    labels: list[str] = Field(default_factory=list)
    values: list[float] = Field(default_factory=list)
    unit: str = "người"
