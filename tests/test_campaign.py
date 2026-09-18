"""Unit and API tests for the Multi-Format Campaign Empire engine."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from content_factory.models import (
    CampaignGenerateRequest,
    HybridAssetType,
    MultiFormatCampaign,
    ProjectCreate,
    ShortsUpdateRequest,
)
from content_factory.service import ContentFactoryService


def test_service_generate_campaign(service: ContentFactoryService) -> None:
    project = service.create_project(
        ProjectCreate(
            name="Titanic Documentary",
            topic="Thảm họa Titanic 1912",
            target_language="vi",
            duration_target_seconds=600,
        )
    )

    campaign = service.generate_campaign(
        project.id,
        CampaignGenerateRequest(shorts_count=5, youtube_target_minutes=10),
    )

    assert isinstance(campaign, MultiFormatCampaign)
    assert campaign.project_id == project.id
    assert "Titanic" in campaign.master_topic

    # YouTube Master
    assert len(campaign.youtube_story_structure) == 8
    assert "hook" in campaign.youtube_story_structure
    assert "climax" in campaign.youtube_story_structure
    assert len(campaign.youtube_scenes) >= 10
    assert len(campaign.youtube_titles) == 5
    assert len(campaign.youtube_chapters) >= 5
    assert "⏱️ MỐC THỜI GIAN" in campaign.youtube_description

    # Hybrid Asset Ratio validation
    asset_types = {s["asset_type"] for s in campaign.youtube_scenes}
    assert HybridAssetType.AI_RECONSTRUCTION in asset_types
    assert HybridAssetType.HISTORICAL_PHOTO in asset_types
    assert HybridAssetType.DYNAMIC_MAP in asset_types
    assert HybridAssetType.DECLASSIFIED_DOC in asset_types
    assert HybridAssetType.TECHNICAL_DIAGRAM in asset_types
    assert HybridAssetType.KINETIC_MOTION in asset_types

    # Shorts variants
    assert len(campaign.shorts) == 5
    first_short = campaign.shorts[0]
    assert first_short.title
    assert first_short.hook
    assert first_short.script
    assert len(first_short.scenes) >= 3
    assert first_short.video_prompts

    # Prompt pack
    assert len(campaign.prompt_pack.kling_veo_prompts) >= 2
    assert len(campaign.prompt_pack.midjourney_prompts) >= 2
    assert len(campaign.prompt_pack.suno_prompts) >= 2
    assert "stability" in campaign.prompt_pack.elevenlabs_settings["voice_settings"]

    # Retention hooks
    assert len(campaign.tiktok_hooks) == 10


def test_api_campaign_lifecycle(client: TestClient) -> None:
    # 1. Create project
    created = client.post(
        "/projects",
        json={
            "name": "Kursk Disaster",
            "topic": "Thảm họa tàu ngầm hạt nhân Kursk K-141",
            "target_language": "vi",
            "duration_target_seconds": 600,
        },
    )
    assert created.status_code == 201
    project_id = created.json()["id"]

    # 2. Generate campaign
    gen_res = client.post(
        f"/projects/{project_id}/campaign/generate",
        json={"shorts_count": 6, "youtube_target_minutes": 12},
    )
    assert gen_res.status_code == 200, gen_res.text
    campaign = gen_res.json()
    assert campaign["project_id"] == project_id
    assert len(campaign["shorts"]) == 6
    assert campaign["youtube_duration_target_seconds"] == 720

    # 3. Get campaign
    get_res = client.get(f"/projects/{project_id}/campaign")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == campaign["id"]

    # 4. Update short
    short_id = campaign["shorts"][0]["id"]
    update_res = client.put(
        f"/projects/{project_id}/campaign/shorts/{short_id}",
        json={
            "title": "Tiêu đề mới giật gân",
            "hook": "0-3s Hook tùy biến đỉnh cao",
            "call_to_action": "Bấm follow ngay để nhận tài liệu!",
        },
    )
    assert update_res.status_code == 200
    updated_short = update_res.json()
    assert updated_short["title"] == "Tiêu đề mới giật gân"
    assert updated_short["hook"] == "0-3s Hook tùy biến đỉnh cao"
    assert updated_short["call_to_action"] == "Bấm follow ngay để nhận tài liệu!"

    # 5. Export campaign pack
    export_res = client.get(f"/projects/{project_id}/campaign/export-pack")
    assert export_res.status_code == 200
    pack = export_res.json()
    assert pack["project_id"] == project_id
    assert "youtube_master" in pack
    assert "shorts" in pack
    assert "prompt_pack" in pack
    assert "fact_check_summary" in pack


def test_service_update_short_not_found(service: ContentFactoryService) -> None:
    project = service.create_project(
        ProjectCreate(
            name="Test",
            topic="Test Topic",
            target_language="vi",
            duration_target_seconds=60,
        )
    )
    service.generate_campaign(project.id)

    with pytest.raises(Exception, match=r"(?i)not found"):
        service.update_short(
            project.id, "non_existent_short", ShortsUpdateRequest(title="X")
        )
