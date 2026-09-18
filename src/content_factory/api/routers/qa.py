"""QA, traceability, media-intelligence and production-booster endpoints.

Exposes the new additive modules over HTTP so the web app and external agents
can use them without touching the core pipeline:

  * QA / risk  -> `compliance.py` (platform, brand, copyright)
  * Traceability -> `audit.py` (provenance log) + `cost_guard.py` (cost gate)
  * Media intelligence -> `dedup.py` + `search.py`
  * Production boosters -> `virality.py`, `audio.py` (ducking), `thumbnail.py`

All of these are deterministic/offline; none bypass the two human gates.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from ...models import (
    AuditRecordRequest,
    BrandCheckRequest,
    CopyrightCheckRequest,
    CostCheckRequest,
    DedupRequest,
    DuckRequest,
    PlatformCheckRequest,
    SimplifySubtitlesRequest,
    ThumbnailRequest,
    TimelineCommandRequest,
    ViralityRequest,
)
from ...service import ContentFactoryService
from ..deps import guard_value


def build_router(service: ContentFactoryService) -> APIRouter:
    router = APIRouter()

    @router.post("/qa/platform")
    def qa_platform(req: PlatformCheckRequest) -> list[dict[str, Any]]:
        """Review a video against one platform's rules (duration/aspect/words)."""
        return service.qa_platform(req)

    @router.post("/qa/brand")
    def qa_brand(req: BrandCheckRequest) -> list[dict[str, Any]]:
        """Check the video against a brand kit (palette / logo / fonts)."""
        return service.qa_brand(req)

    @router.post("/qa/copyright")
    def qa_copyright(req: CopyrightCheckRequest) -> list[dict[str, Any]]:
        """Flag an exact fingerprint match against a protected set."""
        return service.qa_copyright(req)

    @router.get("/audit")
    def audit_list(limit: int = 100) -> list[dict[str, Any]]:
        """Recent provenance entries (newest first)."""
        return service.audit_list(limit)

    @router.post("/audit/record")
    def audit_record(req: AuditRecordRequest) -> dict[str, Any]:
        """Append one provenance entry (which model, what action, when)."""
        return service.audit_record(req)

    @router.post("/cost/check")
    def cost_check(req: CostCheckRequest) -> dict[str, Any]:
        """Estimate the USD cost of an expensive plan and whether to confirm."""
        return service.cost_check(req)

    @router.post("/media/dedup")
    def media_dedup(req: DedupRequest) -> list[list[str]]:
        """Group media items whose perceptual hashes are near-duplicates."""
        return guard_value(lambda: service.media_dedup(req))

    @router.get("/media/search")
    def media_search(q: str, top_k: int = 10) -> list[dict[str, Any]]:
        """Search the media library by transcript/filename (lexical + embedder)."""
        return service.media_search(q, top_k=top_k)

    @router.post("/script/virality")
    def script_virality(req: ViralityRequest) -> dict[str, Any]:
        """Heuristic pre-publish virality score (hook / pace / length / CTA)."""
        return service.script_virality(req)

    @router.post("/render/duck")
    def render_duck(req: DuckRequest) -> dict[str, Any]:
        """Duck a music bed under a voice track (ffmpeg sidechaincompress)."""
        return guard_value(lambda: service.render_duck(req))

    @router.post("/thumbnail/generate")
    def thumbnail_generate(req: ThumbnailRequest) -> list[dict[str, Any]]:
        """Generate thumbnail candidates from the best frames + CTR prediction."""
        return guard_value(lambda: service.thumbnail_generate(req))

    @router.post("/timeline/command")
    def timeline_command(req: TimelineCommandRequest) -> dict[str, Any]:
        """Apply a natural-language editing instruction to a video project."""
        return service.timeline_command(req)

    @router.post("/subtitles/simplify")
    def subtitles_simplify(req: SimplifySubtitlesRequest) -> dict[str, Any]:
        """Simplify captions for kids / language learners (accessibility)."""
        return service.subtitles_simplify(req)

    return router
