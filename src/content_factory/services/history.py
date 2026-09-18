"""History niche: timelines, fact reconciliation, sensitivity, graphics."""

from __future__ import annotations

from ..map_generator import generate_infographic_svg, generate_route_map_svg
from ..models import (
    FactClaim,
    FactReconciliationReport,
    InfographicSpec,
    MapRouteSpec,
    OnThisDayEvent,
    ResearchSource,
    SensitivityAuditReport,
    StructuredTimeline,
    utcnow,
)
from ..on_this_day import (
    get_events_for_date,
    get_events_for_today,
    search_historical_events,
)
from ..research import extract_structured_timeline, reconcile_facts
from ..sensitivity import audit_sensitivity
from .context import ServiceContext


class HistoryMixin(ServiceContext):
    """History niche: timelines, fact reconciliation, sensitivity, graphics."""

    # --- History & Disaster Niche Extensions ---------------------------------

    def get_on_this_day(
        self, month: int | None = None, day: int | None = None
    ) -> list[OnThisDayEvent]:
        """Fetch historical disaster/aviation/maritime events for a given date."""
        if month is not None and day is not None:
            return get_events_for_date(month, day)
        return get_events_for_today()

    def search_history_events(self, query: str) -> list[OnThisDayEvent]:
        """Search historical catastrophe database by keyword or location."""
        return search_historical_events(query)

    def extract_timeline(self, project_id: str) -> StructuredTimeline:
        """Extract structured timeline with casualties and turning points."""
        project = self.get_project(project_id)
        source_text = project.script or ""
        if not source_text and project.research:
            source_text = " ".join(project.research.key_facts) or (
                project.research.notes or ""
            )
        if not source_text:
            source_text = project.topic or project.name

        extracted = extract_structured_timeline(source_text, topic=project.topic)
        project.structured_timeline = extracted
        project.updated_at = utcnow()
        self._store.save(project)
        return extracted

    def reconcile_project_facts(
        self, project_id: str, claims: list[FactClaim] | None = None
    ) -> FactReconciliationReport:
        """Reconcile facts and verify casualty metrics across multiple sources."""
        project = self.get_project(project_id)
        text_parts = [project.script or "", project.topic or ""]
        sources: list[ResearchSource] = []
        if project.research:
            if project.research.notes:
                text_parts.append(project.research.notes)
            text_parts.extend(project.research.key_facts)
            sources.extend(project.research.sources)
        for doc in project.documents:
            sources.append(
                ResearchSource(
                    id=doc.id,
                    title=doc.title,
                    url=doc.url or "",
                    source_type=doc.source,
                    summary=doc.title,
                    highlights=[],
                )
            )

        combined_text = "\n\n".join(t for t in text_parts if t)
        report = reconcile_facts(claims=claims, text=combined_text, sources=sources)
        project.fact_report = report
        project.updated_at = utcnow()
        self._store.save(project)
        return report

    def audit_project_sensitivity(self, project_id: str) -> SensitivityAuditReport:
        """Audit script for graphic violence, victim respect, and safety."""
        project = self.get_project(project_id)
        casualties: int | None = None
        if project.structured_timeline:
            casualties = project.structured_timeline.total_casualties

        report = audit_sensitivity(
            text=project.script or "",
            topic=project.topic or project.name,
            casualties=casualties,
        )
        project.sensitivity_report = report
        project.updated_at = utcnow()
        self._store.save(project)
        return report

    def generate_map_graphic(self, project_id: str, spec: MapRouteSpec) -> str:
        """Generate a procedural SVG route/epicenter map for a project."""
        self.get_project(project_id)
        return generate_route_map_svg(spec)

    def generate_infographic_graphic(
        self, project_id: str, spec: InfographicSpec
    ) -> str:
        """Generate a procedural SVG comparative infographic for a project."""
        self.get_project(project_id)
        return generate_infographic_svg(spec)
