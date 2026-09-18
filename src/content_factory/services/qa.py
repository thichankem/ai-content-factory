from __future__ import annotations

import hashlib
import json
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
    MediaKind,
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

    def qa_platform_verdict(self, req: PlatformCheckRequest) -> dict[str, Any]:
        """One platform's findings as a verdict a UI can bind to.

        The raw findings list stays the canonical answer (the pipeline wants the
        individual issues, and a dashboard renders them one by one). A UI wants
        the verdict: did it pass, and what should I do about it. Deriving that
        here keeps both clients honest about the same check instead of one of them
        re-implementing "passed" with its own rule.
        """
        issues = self.qa_platform(req)
        return {
            "platform": req.platform,
            "passed": not any(item["severity"] in {"error", "fail"} for item in issues),
            "issues": [item["message"] for item in issues],
            "recommendations": [item["hint"] for item in issues if item.get("hint")],
            "findings": issues,
        }

    def qa_brand_verdict(self, req: BrandCheckRequest) -> dict[str, Any]:
        """The brand check as a verdict: pass/fail plus categorised findings."""
        issues = self.qa_brand(req)
        return {
            "passed": not any(item["severity"] in {"error", "fail"} for item in issues),
            "findings": [
                {
                    "category": item["code"],
                    "status": "fail"
                    if item["severity"] in {"error", "fail"}
                    else "warn",
                    "message": item["message"],
                    "hint": item["hint"],
                }
                for item in issues
            ],
        }

    def qa_copyright(self, req: CopyrightCheckRequest) -> list[dict[str, Any]]:
        """Flag every supplied fingerprint that matches the protected set."""
        findings: list[dict[str, Any]] = []
        for candidate in req.candidates:
            for issue in check_copyright(candidate, tuple(req.protected)):
                item = _issue_dict(issue)
                item["asset_id"] = candidate
                findings.append(item)
        return findings

    def qa_copyright_verdict(self, req: CopyrightCheckRequest) -> dict[str, Any]:
        """The copyright check as a verdict, with one row per checked asset."""
        issues = self.qa_copyright(req)
        flagged = {item.get("asset_id") for item in issues}
        return {
            "passed": not issues,
            "fingerprints": [
                {
                    "asset_id": candidate,
                    "sha256": candidate,
                    "status": "flagged" if candidate in flagged else "clear",
                }
                for candidate in req.candidates
            ],
            "findings": issues,
        }

    @staticmethod
    def _audit_row(entry: Any) -> dict[str, Any]:
        """One provenance entry, in both the raw and the client-facing names.

        The log stores ``ts``; the web clients render ``timestamp`` and expect a
        stable ``id`` and a tamper-evident ``sha256_hash``. Rather than rename the
        stored field (which would invalidate existing logs), the row carries both
        spellings and derives the hash from the entry's own content.
        """
        row = dict(entry.__dict__)
        row["timestamp"] = row.get("ts", "")
        row["id"] = hashlib.sha256(
            f"{row.get('ts')}|{row.get('actor')}|{row.get('action')}"
            f"|{row.get('project_id')}|{row.get('media_id')}".encode()
        ).hexdigest()[:16]
        row["sha256_hash"] = hashlib.sha256(
            json.dumps(row, sort_keys=True, default=str).encode()
        ).hexdigest()
        row["hash"] = row["sha256_hash"]
        return row

    def audit_list(self, limit: int = 100) -> list[dict[str, Any]]:
        log = AuditLog(self.settings.audit_dir)
        return [self._audit_row(entry) for entry in log.entries(limit)]

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
        return self._audit_row(entry)

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
            # Same numbers, in the names the web clients read. Kept as aliases
            # rather than replacements so the CLI and agent tools, which use
            # estimate_usd/breakdown, keep working unchanged.
            "by_kind": estimate.breakdown,
            "estimated_total_usd": estimate.total_usd,
            "exceeds_budget": needs_confirmation,
            "budget_limit": settings.cost_guard_threshold_usd,
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
        """Score a script, in both the raw and the per-axis view UIs render.

        ``breakdown`` is the weighted contribution of each axis (hook 0-30, pace
        0-30, length 0-20, CTA 0-20), which is what makes ``score`` add up and is
        what the pipeline reports. A gauge needs each axis **as a percentage of
        its own maximum**, so ``hook_score`` and friends rescale to 0-100 here
        rather than making every client re-derive the weights.
        """
        result = score_virality(
            req.text, duration_seconds=req.duration_seconds, hook=req.hook
        )
        breakdown = result.breakdown

        def axis(key: str, maximum: float) -> float:
            return round(100.0 * float(breakdown.get(key, 0.0)) / maximum, 1)

        return {
            "score": result.score,
            "breakdown": breakdown,
            "warnings": result.warnings,
            "hook_score": axis("hook", 30.0),
            "pacing_score": axis("pace", 30.0),
            "duration_score": axis("length", 20.0),
            "cta_score": axis("cta", 20.0),
            "advice": list(result.warnings),
            "feedback": list(result.warnings),
            "topic": req.topic or "",
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

    def _thumbnail_source(self, req: ThumbnailRequest) -> str | None:
        """Resolve the clip to draw frames from, or ``None`` when there is none.

        Order is deliberate: an explicit id or path always wins; a project falls
        back to the media it was built from; and finally the newest video asset
        stands in, so a UI opened on a fresh session can still preview thumbnail
        candidates instead of failing on a missing id.
        """
        if req.media_id:
            return self._qa_media_path(req.media_id)
        if req.media_path:
            given = Path(req.media_path)
            return str(given) if given.is_file() else None
        if req.project_id:
            project = self.get_project(req.project_id)
            if project.source_media_id:
                source = self.media_path(project.source_media_id)
                if source is not None:
                    return str(source)
        videos = [
            item
            for item in self.media_list()
            if item.kind == MediaKind.VIDEO and item.url
        ]
        if not videos:
            return None
        newest = max(videos, key=lambda item: item.created_at)
        fallback = self.media_path(newest.id)
        return str(fallback) if fallback is not None else None

    def thumbnail_empty_reason(self, req: ThumbnailRequest) -> str:
        """Why no candidates were produced, in terms the caller can act on."""
        if req.media_id or req.media_path or req.project_id:
            return (
                "The source could not be read, so no frames were extracted. "
                "Check that the media still exists and is a video."
            )
        return (
            "No source video was given and the library holds none, so there are "
            "no frames to choose from. Pass media_id / media_path / project_id, "
            "or upload a video first."
        )

    def thumbnail_generate(self, req: ThumbnailRequest) -> list[dict[str, Any]]:
        """Frame candidates plus the CTR prediction, or nothing to draw from."""
        source = self._thumbnail_source(req)
        if source is None:
            return []
        out_dir = str(
            Path(tempfile.gettempdir()) / f"cf-thumbs-{uuid.uuid4().hex[:12]}"
        )
        candidates = generate_thumbnails(
            source,
            out_dir,
            top_k=req.limit,
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
