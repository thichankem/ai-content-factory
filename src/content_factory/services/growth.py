"""Multi-format campaigns and externally generated asset ingestion."""

from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Any

from ..campaign import generate_campaign_for_project
from ..models import (
    CampaignGenerateRequest,
    ExternalAssetRecord,
    ExternalAssetType,
    ExternalImportRequest,
    MultiFormatCampaign,
    ResearchSource,
    ShortsUpdateRequest,
    ShortsVariant,
    VoiceoverBundle,
    VoiceoverTrack,
    utcnow,
)
from .context import ServiceContext
from .errors import (
    NotFoundError,
)


class GrowthMixin(ServiceContext):
    """Multi-format campaigns and externally generated asset ingestion."""

    # --- Multi-Format Campaign -----------------------------------------------

    def generate_campaign(
        self,
        project_id: str,
        request: CampaignGenerateRequest | None = None,
    ) -> MultiFormatCampaign:
        """Generate a full multi-format campaign with 15-asset package."""
        project = self.get_project(project_id)
        campaign = generate_campaign_for_project(project, request)
        project.campaign = campaign
        self._store.save(project)
        return campaign

    def get_campaign(self, project_id: str) -> MultiFormatCampaign:
        """Retrieve existing campaign or generate on-demand if none exists."""
        project = self.get_project(project_id)
        if project.campaign is None:
            return self.generate_campaign(project_id)
        return project.campaign

    def update_short(
        self,
        project_id: str,
        short_id: str,
        request: ShortsUpdateRequest,
    ) -> ShortsVariant:
        """Update text or call-to-action for a specific short in the campaign."""
        project = self.get_project(project_id)
        if project.campaign is None:
            raise NotFoundError("Project does not have an active campaign.")

        target_short: ShortsVariant | None = None
        for s in project.campaign.shorts:
            if s.id == short_id:
                target_short = s
                break

        if target_short is None:
            raise NotFoundError(f"Short {short_id} not found in campaign.")

        if request.title is not None:
            target_short.title = request.title
        if request.script is not None:
            target_short.script = request.script
        if request.hook is not None:
            target_short.hook = request.hook
        if request.call_to_action is not None:
            target_short.call_to_action = request.call_to_action

        project.campaign.updated_at = utcnow()
        self._store.save(project)
        return target_short

    def export_campaign_pack(self, project_id: str) -> dict[str, Any]:
        """Bundle the 15-asset empire package for export or 3rd party AI consumption."""
        campaign = self.get_campaign(project_id)
        return {
            "campaign_id": campaign.id,
            "project_id": campaign.project_id,
            "master_topic": campaign.master_topic,
            "asset_ratio": campaign.asset_ratio.model_dump(),
            "youtube_master": {
                "titles": campaign.youtube_titles,
                "script": campaign.youtube_script,
                "story_structure": campaign.youtube_story_structure,
                "scenes": campaign.youtube_scenes,
                "description": campaign.youtube_description,
                "chapters": campaign.youtube_chapters,
            },
            "shorts": [s.model_dump() for s in campaign.shorts],
            "tiktok_hooks": campaign.tiktok_hooks,
            "thumbnail_prompts": campaign.thumbnail_prompts,
            "prompt_pack": campaign.prompt_pack.model_dump(),
            "fact_check_summary": campaign.fact_check_summary,
            "created_at": campaign.created_at.isoformat(),
            "updated_at": campaign.updated_at.isoformat(),
        }

    # --- External Results & Asset Ingestion -----------------------------------

    def import_external_asset(
        self, project_id: str, request: ExternalImportRequest
    ) -> ExternalAssetRecord:
        """Ingest a 3rd-party AI asset (Kling/Veo, Midjourney, ElevenLabs, Suno)."""
        project = self.get_project(project_id)
        asset_id = uuid.uuid4().hex[:10]
        url = request.url or ""

        record = ExternalAssetRecord(
            id=asset_id,
            project_id=project.id,
            asset_type=request.asset_type,
            scene_id=request.scene_id,
            url=url,
            label=request.label or f"{request.asset_type.value} import",
            attribution=request.attribution,
            created_at=utcnow(),
        )

        # 1. Bind to scene if requested
        if (
            request.asset_type
            in (
                ExternalAssetType.SCENE_VIDEO,
                ExternalAssetType.SCENE_IMAGE,
            )
            and project.video_project
        ):
            target_scene = None
            if request.scene_id:
                target_scene = next(
                    (
                        s
                        for s in project.video_project.scenes
                        if s.id == request.scene_id
                    ),
                    None,
                )
            elif request.scene_index is not None and 0 <= request.scene_index < len(
                project.video_project.scenes
            ):
                target_scene = project.video_project.scenes[request.scene_index]

            if target_scene:
                if request.asset_type == ExternalAssetType.SCENE_VIDEO:
                    target_scene.video_url = url
                    target_scene.asset_type = "ai_reconstruction"
                else:
                    target_scene.image_url = url
                    target_scene.asset_type = "historical_photo"
                if request.attribution:
                    target_scene.source_attribution = request.attribution
                record.scene_id = target_scene.id

        # 2. Voiceover track
        elif request.asset_type == ExternalAssetType.VOICEOVER:
            if url:
                if project.voiceover is None:
                    project.voiceover = VoiceoverBundle(
                        engine="external",
                        tracks=[],
                        generated_at=utcnow(),
                    )
                track_id = request.scene_id or (
                    project.video_project.scenes[0].id
                    if project.video_project and project.video_project.scenes
                    else "main"
                )
                project.voiceover.tracks.append(
                    VoiceoverTrack(
                        scene_id=track_id,
                        audio_url=url,
                        duration_seconds=request.metadata.get("duration", 5.0),
                        text=request.label or "",
                    )
                )

        # 3. Background Music (Suno / Udio)
        elif request.asset_type == ExternalAssetType.BACKGROUND_MUSIC:
            if project.video_project:
                project.video_project.background_music = True
                project.video_project.background_music_url = url
                project.video_project.music_volume = float(
                    request.metadata.get("volume", 0.35)
                )

        # 4. Research Dossier & Fact Check (Perplexity / DeepResearch)
        elif request.asset_type in (
            ExternalAssetType.RESEARCH_DOSSIER,
            ExternalAssetType.FACT_CHECK_REPORT,
        ):
            if request.raw_content:
                from ..models import ResearchBundle

                if project.research is None:
                    project.research = ResearchBundle(
                        sources=[],
                        key_facts=[],
                    )
                lines = [
                    line.strip()
                    for line in request.raw_content.splitlines()
                    if line.strip()
                ]
                facts = [
                    line.lstrip("*-#0123456789. ")
                    for line in lines
                    if len(line) > 10 and not line.startswith("http")
                ]
                sources = [
                    ResearchSource(
                        id=uuid.uuid4().hex[:8],
                        title=request.attribution or "External AI Dossier",
                        url=line if line.startswith("http") else "",
                        source_type="external_ai",
                        summary=line[:200],
                    )
                    for line in lines
                    if line.startswith("http")
                ]
                project.research.key_facts.extend(facts[:10])
                if sources:
                    project.research.sources.extend(sources[:5])

        project.external_assets.append(record)
        project.updated_at = utcnow()
        self._store.save(project)
        return record

    def upload_external_file(
        self,
        project_id: str,
        filename: str,
        content: bytes,
        asset_type: ExternalAssetType,
        scene_id: str | None = None,
        attribution: str | None = None,
    ) -> ExternalAssetRecord:
        """Upload media bytes, store on disk, and register external asset."""
        self.get_project(project_id)
        clean_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", filename).strip("_") or "file"
        save_dir = Path(self._settings.uploads_dir) / project_id
        save_dir.mkdir(parents=True, exist_ok=True)
        file_path = save_dir / f"{uuid.uuid4().hex[:6]}_{clean_name}"
        file_path.write_bytes(content)

        relative_url = f"/uploads/{project_id}/{file_path.name}"
        req = ExternalImportRequest(
            asset_type=asset_type,
            scene_id=scene_id,
            url=relative_url,
            label=filename,
            attribution=attribution or "Local Upload",
        )
        return self.import_external_asset(project_id, req)

    def batch_import_external_assets(
        self, project_id: str, requests: list[ExternalImportRequest]
    ) -> list[ExternalAssetRecord]:
        """Batch import multiple external assets into a project."""
        results = []
        for req in requests:
            results.append(self.import_external_asset(project_id, req))
        return results

    def list_external_assets(self, project_id: str) -> list[ExternalAssetRecord]:
        """List all external assets attached to a project."""
        project = self.get_project(project_id)
        return project.external_assets
