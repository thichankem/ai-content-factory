"""SEO endpoints: score, optimise and statistically test a publish pack.

One surface per question a creator or an agent asks before publishing:

* ``GET  /seo/rules``         — the thresholds and signal weights themselves
* ``POST /seo/score``         — how ready is this pack, and what is it worth
* ``POST /seo/optimize``      — the rewrite plus the gain it actually buys
* ``POST /seo/ab/plan``       — how many impressions a real test needs
* ``POST /seo/ab/evaluate``   — did the variant really win (p-value, CI, lift)
* ``POST /seo/keywords``      — demand vs competition, and winning phrasings
* ``POST /seo/calibrate``     — learn the weights from this channel's results
* ``POST /projects/{id}/seo`` — score what the project would actually ship

Everything is deterministic and offline: no API key, no scraping, no platform
call. When a real analytics export arrives it is passed in, so the loop closes
on measured numbers instead of assumptions.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from ...models import (
    SEO_METRICS,
    SEO_PLATFORMS,
    SeoAbEvaluateRequest,
    SeoAbPlanRequest,
    SeoCalibrateRequest,
    SeoKeywordRequest,
    SeoOptimizeRequest,
    SeoProjectScoreRequest,
    SeoScoreRequest,
)
from ...service import ContentFactoryService
from ..deps import get_or_404


def _platform(value: str) -> str:
    key = (value or "").strip().lower()
    if key not in SEO_PLATFORMS:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown platform '{value}'. Use one of {list(SEO_PLATFORMS)}.",
        )
    return key


def _metric(value: str) -> str:
    key = (value or "").strip().lower()
    if key not in SEO_METRICS:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown metric '{value}'. Use one of {list(SEO_METRICS)}.",
        )
    return key


def build_router(service: ContentFactoryService) -> APIRouter:

    router = APIRouter()

    @router.get("/seo/rules")
    def seo_rules() -> list[dict[str, Any]]:
        """Platform thresholds, targets and the full weighted signal table."""
        return service.seo_rules()

    @router.post("/seo/score")
    def seo_score(req: SeoScoreRequest) -> dict[str, Any]:
        """Score a pack for one platform ('all' scores every platform)."""
        return service.seo_score(_platform(req.platform), req.pack.to_engine())

    @router.post("/seo/optimize")
    def seo_optimize(req: SeoOptimizeRequest) -> dict[str, Any]:
        """Rewrite a pack for the maximum score and report the measured gain."""
        return service.seo_optimize(_platform(req.platform), req.pack.to_engine())

    @router.post("/seo/ab/plan")
    def seo_ab_plan(req: SeoAbPlanRequest) -> dict[str, Any]:
        """Sample size, calendar days and the decision rule for an A/B test."""
        return service.seo_ab_plan(
            _metric(req.metric),
            req.baseline_rate,
            relative_lift=req.relative_lift,
            daily_traffic=req.daily_traffic,
            arms=req.arms,
            alpha=req.alpha,
            power=req.power,
        )

    @router.post("/seo/ab/evaluate")
    def seo_ab_evaluate(req: SeoAbEvaluateRequest) -> dict[str, Any]:
        """Test whether a variant beat the control, with p-value and intervals."""
        return service.seo_ab_evaluate(
            _metric(req.metric),
            [arm.model_dump() for arm in req.arms],
            alpha=req.alpha,
            relative_lift=req.relative_lift,
        )

    @router.post("/seo/keywords")
    def seo_keywords(req: SeoKeywordRequest) -> dict[str, Any]:
        """Rank phrases by demand vs competition and mine winning phrasings."""
        pack = req.pack.to_engine() if req.pack else None
        return service.seo_keywords(
            req.keywords,
            [row.model_dump() for row in req.competitors],
            pack=pack,
        )

    @router.post("/seo/calibrate")
    def seo_calibrate(req: SeoCalibrateRequest) -> dict[str, Any]:
        """Correlate each signal with real outcomes and suggest new weights."""
        return service.seo_calibrate(
            [(row.signals, row.outcome) for row in req.observations],
            _platform(req.platform),
            outcome=req.outcome,
        )

    @router.post("/projects/{project_id}/seo")
    def project_seo(project_id: str, req: SeoProjectScoreRequest) -> dict[str, Any]:
        """Score the pack this project would actually publish."""
        get_or_404(service, project_id)
        engagement = req.engagement.to_engine() if req.engagement else None
        return service.seo_score_project(
            project_id,
            _platform(req.platform),
            keywords=req.keywords or None,
            publish_hour=req.publish_hour,
            audience_hours=req.audience_hours,
            description=req.description,
            tags=req.tags,
            hashtags=req.hashtags,
            title=req.title,
            engagement=engagement,
        )

    return router
