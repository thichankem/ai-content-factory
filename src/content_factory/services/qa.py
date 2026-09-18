from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import Any

from ..audio import duck_music_under_speech
from ..audit import AuditLog
from ..compliance import (
    BrandKit,
    BrandMeta,
    ComplianceIssue,
    ComplianceMeta,
    check_brand,
    check_copyright,
    check_platform,
)
from ..cost_guard import CostGuard, PlanBudget
from ..dedup import find_near_duplicates, image_hash
from ..models import (
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
from ..nl_timeline import apply_command
from ..search import MediaSearchIndex
from ..simple_subtitles import SimplificationLevel, simplify_captions
from ..thumbnail import generate_thumbnails
from ..virality import score_virality
from .errors import NotFoundError
from .media import MediaMixin


def _issue_dict(issue: ComplianceIssue) -> dict[str, Any]:
    return {
        "code": issue.code,
        "severity": issue.severity.value,
        "message": issue.message,
        "hint": issue.hint,
    }


class QaMixin(MediaMixin):
    def _qa_media_path(self, media_id: str) -> str:
        path = self.media_path(media_id)
        if path is None:
            raise NotFoundError(f"Media '{media_id}' not found")
        return str(path)

    def qa_platform(self, req: PlatformCheckRequest) -> list[dict[str, Any]]:
        meta = ComplianceMeta(
            duration_seconds=req.duration_seconds,
            aspect_ratio=req.aspect_ratio,
            words=req.words,
            text=req.text,
        )
        return [_issue_dict(issue) for issue in check_platform(meta, req.platform)]

    def qa_brand(self, req: BrandCheckRequest) -> list[dict[str, Any]]:
        kit = BrandKit(
            palette=tuple(req.palette),
            fonts=tuple(req.fonts),
            logo_fingerprints=tuple(req.logo_fingerprints),
        )
        meta = BrandMeta(
            dominant_colors=tuple(req.dominant_colors),
            fonts_used=tuple(req.fonts_used),
            has_logo=req.has_logo,
        )
        return [_issue_dict(issue) for issue in check_brand(meta, kit)]

    def qa_copyright(self, req: CopyrightCheckRequest) -> list[dict[str, Any]]:
        return [
            _issue_dict(issue)
            for issue in check_copyright(req.fingerprint, tuple(req.protected))
        ]

    def audit_list(self, limit: int = 100) -> list[dict[str, Any]]:
        log = AuditLog(self.settings.audit_dir)
        return [entry.__dict__ for entry in log.entries(limit)]

    def audit_record(self, req: AuditRecordRequest) -> dict[str, Any]:
        log = AuditLog(self.settings.audit_dir)
        entry = log.record(
            req.actor,
            req.action,
            project_id=req.project_id,
            media_id=req.media_id,
            prompt=req.prompt,
            detail=req.detail,
        )
        return entry.__dict__

    def cost_check(self, req: CostCheckRequest) -> dict[str, Any]:
        settings = self.settings
        budget = PlanBudget(
            enabled=settings.cost_guard_enabled,
            threshold_usd=settings.cost_guard_threshold_usd,
            unit_costs={
                "vision": settings.cost_unit_vision_usd,
                "audio_llm": settings.cost_unit_audio_llm_usd,
                "tts": settings.cost_unit_tts_usd,
                "stt": settings.cost_unit_stt_usd,
                "embedding": settings.cost_unit_embedding_usd,
            },
        )
        estimate, needs_confirmation = CostGuard(budget).check(req.calls)
        return {
            "estimate_usd": estimate.total_usd,
            "breakdown": estimate.breakdown,
            "needs_confirmation": needs_confirmation,
        }

    def media_dedup(self, req: DedupRequest) -> list[list[str]]:
        hashes: dict[str, str] = {}
        for media_id in req.media_ids:
            try:
                hashes[media_id] = image_hash(self._qa_media_path(media_id))
            except ValueError:
                continue
        return find_near_duplicates(
            hashes, max_distance=self.settings.dedup_max_distance
        )

    def media_search(self, q: str, top_k: int = 10) -> list[dict[str, Any]]:
        index = MediaSearchIndex()
        for item in self.media_list():
            text = item.transcription or item.text_content or ""
            index.add(item.id, item.filename, item.kind.value, text)
        return [hit.__dict__ for hit in index.search(q, top_k=top_k)]

    def script_virality(self, req: ViralityRequest) -> dict[str, Any]:
        result = score_virality(
            req.script, duration_seconds=req.duration_seconds, hook=req.hook
        )
        return {
            "score": result.score,
            "breakdown": result.breakdown,
            "warnings": result.warnings,
        }

    def render_duck(self, req: DuckRequest) -> dict[str, Any]:
        out = req.out or str(
            Path(tempfile.gettempdir()) / f"cf-duck-{uuid.uuid4().hex[:12]}.mp3"
        )
        out_path = duck_music_under_speech(
            self._qa_media_path(req.music_media_id),
            self._qa_media_path(req.voice_media_id),
            out,
        )
        return {"out": out_path}

    def thumbnail_generate(self, req: ThumbnailRequest) -> list[dict[str, Any]]:
        out_dir = str(
            Path(tempfile.gettempdir()) / f"cf-thumbs-{uuid.uuid4().hex[:12]}"
        )
        candidates = generate_thumbnails(
            self._qa_media_path(req.media_id),
            out_dir,
            top_k=req.top_k,
            overlays=tuple(req.overlays),
        )
        return [candidate.__dict__ for candidate in candidates]

    def timeline_command(self, req: TimelineCommandRequest) -> dict[str, Any]:
        updated, command = apply_command(req.project, req.text)
        return {
            "project": updated.model_dump(),
            "command": {
                "intent": command.intent.value,
                "target": command.target,
                "description": command.description,
            },
        }

    def subtitles_simplify(self, req: SimplifySubtitlesRequest) -> dict[str, Any]:
        level = SimplificationLevel(req.level)
        results = simplify_captions(req.captions, level)
        return {
            "level": level.value,
            "captions": [
                {"original": r.original, "simplified": r.simplified} for r in results
            ],
        }
