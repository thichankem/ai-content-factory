"""Unit and API tests for the external AI results ingestion flow."""

from __future__ import annotations

import io

from fastapi.testclient import TestClient

from content_factory.models import (
    ApprovalCreate,
    ApprovalStage,
    ApprovalVerdict,
    ExternalAssetType,
    ExternalImportRequest,
    Project,
    ProjectCreate,
    ScriptUpdate,
    WorkflowNode,
    WorkflowNodeType,
    WorkflowRunRequest,
)
from content_factory.service import ContentFactoryService


def _create_approved_video_project(
    service: ContentFactoryService, name: str, topic: str
) -> Project:
    project = service.create_project(
        ProjectCreate(
            name=name,
            topic=topic,
            target_language="vi",
            duration_target_seconds=60,
        )
    )
    service.update_script(
        project.id,
        ScriptUpdate(
            script="[Hook]\nTest hook\n[Turn]\nTest turn\n[Payoff]\nTest payoff",
            source_rights_confirmed=True,
        ),
    )
    service.approve(
        project.id,
        ApprovalCreate(
            stage=ApprovalStage.SCRIPT,
            verdict=ApprovalVerdict.APPROVED,
            comment="Approved for video production",
        ),
    )
    return service.produce_video(project.id)


def test_service_import_external_assets(service: ContentFactoryService) -> None:
    # 1. Create project and produce video project
    project = _create_approved_video_project(
        service,
        name="Kursk Ingest Test",
        topic="Thảm họa tàu ngầm hạt nhân Kursk",
    )

    # 2. Ingest external video (Kling AI) into Scene 1
    p = service.get_project(project.id)
    assert p.video_project is not None
    scene_1 = p.video_project.scenes[0]

    record_video = service.import_external_asset(
        project.id,
        ExternalImportRequest(
            asset_type=ExternalAssetType.SCENE_VIDEO,
            scene_id=scene_1.id,
            url="https://assets.klingai.com/renders/kursk_explosion_1080p.mp4",
            label="Kling AI 1080p Torpedo Compartment",
            attribution="Kling 1.5 Pro AI",
        ),
    )
    assert record_video.scene_id == scene_1.id
    assert "kursk_explosion" in (record_video.url or "")

    # Verify scene was updated
    p = service.get_project(project.id)
    assert p.video_project is not None
    s1_updated = p.video_project.scenes[0]
    assert (
        s1_updated.video_url
        == "https://assets.klingai.com/renders/kursk_explosion_1080p.mp4"
    )
    assert s1_updated.source_attribution == "Kling 1.5 Pro AI"
    assert s1_updated.asset_type == "ai_reconstruction"

    # 3. Ingest external image (Midjourney) into Scene 2
    if len(p.video_project.scenes) > 1:
        scene_2 = p.video_project.scenes[1]
        record_img = service.import_external_asset(
            project.id,
            ExternalImportRequest(
                asset_type=ExternalAssetType.SCENE_IMAGE,
                scene_id=scene_2.id,
                url="https://cdn.midjourney.com/archives/kursk_captain.png",
                label="Captain Kolesnikov Portrait",
                attribution="Midjourney v6.1",
            ),
        )
        assert record_img.scene_id == scene_2.id
        p = service.get_project(project.id)
        assert p.video_project is not None
        assert p.video_project.scenes[1].image_url == (
            "https://cdn.midjourney.com/archives/kursk_captain.png"
        )
        assert p.video_project.scenes[1].source_attribution == "Midjourney v6.1"

    # 4. Ingest Background Music (Suno AI)
    record_music = service.import_external_asset(
        project.id,
        ExternalImportRequest(
            asset_type=ExternalAssetType.BACKGROUND_MUSIC,
            url="https://cdn1.suno.ai/tracks/deep_ocean_somber.mp3",
            label="Deep Ocean Somber Orchestral",
            attribution="Suno AI v4",
            metadata={"volume": 0.4},
        ),
    )
    assert record_music.asset_type == ExternalAssetType.BACKGROUND_MUSIC
    p = service.get_project(project.id)
    assert p.video_project is not None
    assert p.video_project.background_music is True
    assert p.video_project.background_music_url == (
        "https://cdn1.suno.ai/tracks/deep_ocean_somber.mp3"
    )

    # 5. Ingest External Research Dossier (Perplexity / DeepResearch)
    dossier_text = (
        "Torpedo explosion in compartment 1 triggered massive secondary blast.\n"
        "23 sailors survived in compartment 9 for several hours.\n"
        "https://en.wikipedia.org/wiki/Kursk_submarine_disaster\n"
        "Dmitry Kolesnikov left a handwritten farewell note to his wife Olga.\n"
    )
    record_research = service.import_external_asset(
        project.id,
        ExternalImportRequest(
            asset_type=ExternalAssetType.RESEARCH_DOSSIER,
            raw_content=dossier_text,
            attribution="Perplexity DeepResearch",
        ),
    )
    assert record_research.asset_type == ExternalAssetType.RESEARCH_DOSSIER
    p = service.get_project(project.id)
    assert p.research is not None
    assert len(p.research.key_facts) >= 3
    assert len(p.research.sources) >= 1

    # 6. List all external assets
    all_assets = service.list_external_assets(project.id)
    assert len(all_assets) >= 4


def test_api_external_ingest_endpoints(client: TestClient) -> None:
    # 1. Create project
    res = client.post(
        "/projects",
        json={
            "name": "Titanic External Media Test",
            "topic": "Thảm họa Titanic 1912",
            "target_language": "vi",
            "duration_target_seconds": 60,
        },
    )
    assert res.status_code == 201
    project_id = res.json()["id"]

    # Produce scenes
    client.post(f"/projects/{project_id}/generate")

    # 2. POST /projects/{id}/external/import (Link URL)
    import_res = client.post(
        f"/projects/{project_id}/external/import",
        json={
            "asset_type": "scene_video",
            "scene_index": 0,
            "url": "https://veo.google.com/renders/titanic_sinking.mp4",
            "label": "Veo 2 Cinematic Sinking",
            "attribution": "Google Veo 2",
        },
    )
    assert import_res.status_code == 200, import_res.text
    record = import_res.json()
    assert record["asset_type"] == "scene_video"
    assert record["attribution"] == "Google Veo 2"

    # 3. POST /projects/{id}/external/upload (File Upload)
    fake_video_bytes = b"FAKE_MP4_VIDEO_HEADER_123456789"
    upload_res = client.post(
        f"/projects/{project_id}/external/upload",
        data={
            "asset_type": "scene_image",
            "attribution": "Midjourney Photo",
        },
        files={
            "file": ("iceberg_night.jpg", io.BytesIO(fake_video_bytes), "image/jpeg"),
        },
    )
    assert upload_res.status_code == 200, upload_res.text
    up_record = upload_res.json()
    assert up_record["asset_type"] == "scene_image"
    assert up_record["url"].startswith("/uploads/")

    # 4. POST /projects/{id}/external/batch-import
    batch_res = client.post(
        f"/projects/{project_id}/external/batch-import",
        json={
            "items": [
                {
                    "asset_type": "voiceover",
                    "url": "https://api.elevenlabs.io/audio/adam_scene_1.mp3",
                    "label": "ElevenLabs Adam Voiceover",
                    "attribution": "ElevenLabs v2",
                },
                {
                    "asset_type": "background_music",
                    "url": "https://cdn.suno.ai/audio/titanic_hymn.mp3",
                    "label": "Nearer My God to Thee",
                    "attribution": "Suno AI",
                },
            ]
        },
    )
    assert batch_res.status_code == 200, batch_res.text
    batch_records = batch_res.json()
    assert len(batch_records) == 2

    # 5. GET /projects/{id}/external/assets
    list_res = client.get(f"/projects/{project_id}/external/assets")
    assert list_res.status_code == 200
    assets = list_res.json()
    assert len(assets) >= 4


def test_workflow_runner_ingest_external_node(service: ContentFactoryService) -> None:
    project = _create_approved_video_project(
        service,
        name="Workflow Ingest Test",
        topic="Thảm họa hàng không",
    )

    # Attach workflow with INGEST_EXTERNAL node
    flow = service.project_workflow(project.id)
    ingest_node = WorkflowNode(
        id="ingest_ext_1",
        type=WorkflowNodeType.INGEST_EXTERNAL,
        label="Ingest External AI Media",
        x=200.0,
        y=100.0,
        params={},
    )
    flow.nodes.append(ingest_node)
    project.workflow = flow
    service._store.save(project)

    # Run workflow with external assets in inputs
    run = service.run_workflow(
        project.id,
        WorkflowRunRequest(
            inputs={
                "external_assets": [
                    {
                        "asset_type": "scene_video",
                        "scene_index": 0,
                        "url": "https://example.com/plane_kling.mp4",
                        "attribution": "Kling AI",
                    }
                ]
            }
        ),
    )
    assert run.status.value in ("ok", "blocked")
    ingest_step = next((s for s in run.steps if s.node_id == "ingest_ext_1"), None)
    assert ingest_step is not None
    assert ingest_step.status.value == "ok"
    assert ingest_step.output["external_assets_count"] >= 1
