"""Project lifecycle: creation, script editing, research and gates."""

from __future__ import annotations

from fastapi import (
    APIRouter,
    HTTPException,
    Response,
)

from ...models import (
    ApprovalCreate,
    DocumentResult,
    FactReconcileRequest,
    FactReconciliationReport,
    GroundRequest,
    Project,
    ProjectCreate,
    PublishCreate,
    ResearchBundle,
    ScriptAnalysis,
    ScriptAnalyzeRequest,
    ScriptStyleSelect,
    ScriptUpdate,
    SensitivityAuditReport,
)
from ...providers import ProviderUnavailableError
from ...service import ContentFactoryService
from ..deps import get_or_404, guard, guard_value, render_thumbnail


def build_router(service: ContentFactoryService) -> APIRouter:

    router = APIRouter()

    @router.post("/projects", response_model=Project, status_code=201)
    async def create_project(data: ProjectCreate) -> Project:
        return service.create_project(data)

    @router.get("/projects", response_model=list[Project])
    async def list_projects() -> list[Project]:
        return service.list_projects()

    @router.get("/projects/{project_id}", response_model=Project)
    async def get_project(project_id: str) -> Project:
        return get_or_404(service, project_id)

    @router.put("/projects/{project_id}/script", response_model=Project)
    async def update_script(project_id: str, data: ScriptUpdate) -> Project:
        return guard(lambda: service.update_script(project_id, data))

    @router.post("/projects/{project_id}/script/generate", response_model=Project)
    async def generate_script(project_id: str) -> Project:
        get_or_404(service, project_id)
        try:
            return await service.generate_script(project_id)
        except ProviderUnavailableError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @router.put("/projects/{project_id}/script/style", response_model=Project)
    async def select_script_style(project_id: str, data: ScriptStyleSelect) -> Project:
        return guard_value(lambda: service.select_script_style(project_id, data.style))

    @router.post("/projects/{project_id}/script/analyze", response_model=ScriptAnalysis)
    async def analyze_script(
        project_id: str, data: ScriptAnalyzeRequest
    ) -> ScriptAnalysis:
        return guard_value(lambda: service.analyze_project_script(project_id, data))

    @router.post("/projects/{project_id}/research", response_model=Project)
    async def run_research(project_id: str, web: bool = True) -> Project:
        get_or_404(service, project_id)
        return await service.research(project_id, include_web=web)

    @router.get("/projects/{project_id}/research", response_model=ResearchBundle)
    async def get_research(project_id: str) -> ResearchBundle:
        project = get_or_404(service, project_id)
        if project.research is None:
            raise HTTPException(status_code=404, detail="No research has been run yet")
        return project.research

    @router.post("/projects/{project_id}/documents", response_model=Project)
    async def add_document(project_id: str, result: DocumentResult) -> Project:
        get_or_404(service, project_id)
        try:
            return await service.add_document(project_id, result)
        except Exception as exc:
            raise HTTPException(
                status_code=502, detail=f"Download failed: {exc}"
            ) from exc

    @router.post("/projects/{project_id}/approvals", response_model=Project)
    async def approve(project_id: str, data: ApprovalCreate) -> Project:
        return guard(lambda: service.approve(project_id, data))

    @router.post("/projects/{project_id}/generate", response_model=Project)
    async def start_generation(project_id: str) -> Project:
        return guard(lambda: service.start_generation(project_id))

    @router.post("/projects/{project_id}/publish", response_model=Project)
    async def publish(project_id: str, data: PublishCreate) -> Project:
        return guard(lambda: service.publish(project_id, data))

    @router.get("/projects/{project_id}/thumbnail")
    async def thumbnail(project_id: str) -> Response:
        project = get_or_404(service, project_id)
        return Response(
            content=render_thumbnail(project),
            media_type="image/svg+xml",
            headers={"Cache-Control": "no-store"},
        )

    @router.put(
        "/projects/{project_id}/knowledge-base",
        response_model=Project,
    )
    def attach_kb_to_project(project_id: str, kb_id: str | None = None) -> Project:
        """Attach (or detach with null) a knowledge base to a project."""
        return guard_value(lambda: service.attach_kb(project_id, kb_id))

    @router.post("/projects/{project_id}/ground", response_model=Project)
    def ground_project(
        project_id: str, payload: GroundRequest | None = None
    ) -> Project:
        """Retrieve knowledge for the topic and store the citation bundle."""
        return guard_value(
            lambda: service.ground_project(project_id, payload or GroundRequest())
        )

    @router.post(
        "/projects/{project_id}/facts/reconcile",
        response_model=FactReconciliationReport,
    )
    def reconcile_project_facts(
        project_id: str, payload: FactReconcileRequest | None = None
    ) -> FactReconciliationReport:
        """Cross-reference casualty and factual claims against sources."""
        claims = payload.claims if payload else None
        return guard_value(
            lambda: service.reconcile_project_facts(project_id, claims=claims)
        )

    @router.post(
        "/projects/{project_id}/sensitivity/audit",
        response_model=SensitivityAuditReport,
    )
    def audit_project_sensitivity(project_id: str) -> SensitivityAuditReport:
        """Audit script for sensitivity, victim dignity, and monetization."""
        return guard_value(lambda: service.audit_project_sensitivity(project_id))

    return router
