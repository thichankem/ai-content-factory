"""HTTP tests for the timeline editing endpoints."""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from content_factory.models import (
    IssueSeverity,
    ProjectCreate,
    ProjectStatus,
    VideoProject,
    VideoScene,
)
from content_factory.service import ContentFactoryService, StateConflictError

SCRIPT = (
    "[Hook]\nThe city whispers before it wakes.\n\n"
    "[Turn]\nTrucks and shutters are the only choir.\n\n"
    "[Payoff]\nListen at 5am and you hear who really runs this place."
)


def _drive_to_review(client: TestClient) -> str:
    """Create and approve a project through the API until video_review."""
    created = client.post(
        "/projects",
        json={
            "name": "Timeline API",
            "topic": "A city at dawn",
            "target_language": "en",
            "duration_target_seconds": 30,
        },
    )
    assert created.status_code == 201, created.text
    project_id = created.json()["id"]
    client.put(
        f"/projects/{project_id}/script",
        json={"script": SCRIPT, "source_rights_confirmed": True},
    )
    client.post(
        f"/projects/{project_id}/approvals",
        json={"stage": "script", "verdict": "approved"},
    )
    client.post(f"/projects/{project_id}/generate")
    for _ in range(300):
        project = client.get(f"/projects/{project_id}").json()
        if project["status"] == "video_review":
            return project_id
        time.sleep(0.02)
    raise AssertionError("the worker never reached video_review")


def _timeline(client: TestClient, project_id: str) -> dict:
    response = client.get(f"/projects/{project_id}/video-project")
    assert response.status_code == 200, response.text
    return response.json()


def _scene_ids(client: TestClient, project_id: str) -> list[str]:
    return [scene["id"] for scene in _timeline(client, project_id)["scenes"]]


@pytest.fixture
def timeline_project(service: ContentFactoryService):
    project = service.create_project(ProjectCreate(name="Timeline", topic="City"))
    project.status = ProjectStatus.VIDEO_REVIEW
    project.script = SCRIPT
    project.video_project = VideoProject(
        revision=17,
        scenes=[
            VideoScene(
                id="first", label="First", text="Hello world", duration_seconds=3
            ),
            VideoScene(
                id="second", label="Second", text="Goodbye world", duration_seconds=4
            ),
        ],
    )
    return project


@pytest.mark.parametrize("status", list(ProjectStatus))
@pytest.mark.parametrize("existing", [False, True])
def test_build_and_rebuild_preserve_original_status_policy(
    service, timeline_project, status, existing
):
    project = timeline_project
    project.status = status
    if not existing:
        project.video_project = None
    before = project.model_copy(deep=True)
    result = service.build_video_project(project.id)
    assert result.video_project.scenes
    assert result.video_project.revision == (18 if existing else 2)
    assert result.video_project.aspect_ratio == "9:16"
    assert result.model_dump(
        exclude={"video_project", "updated_at"}
    ) == before.model_dump(exclude={"video_project", "updated_at"})
    assert project == before


def test_build_does_not_bypass_generation_or_approval_gates(service):
    from content_factory.models import ApprovalCreate, PublishCreate, ScriptUpdate
    from content_factory.service import RightsNotConfirmedError

    project = service.create_project(ProjectCreate(name="Build", topic="City"))
    service.update_script(project.id, ScriptUpdate(script=SCRIPT))
    result = service.build_video_project(project.id)
    assert result.status == ProjectStatus.SCRIPT_REVIEW
    assert result.source_rights_confirmed is False
    assert result.approvals == []
    with pytest.raises(StateConflictError):
        service.start_generation(project.id)
    with pytest.raises(RightsNotConfirmedError):
        service.approve(project.id, ApprovalCreate(stage="script", verdict="approved"))
    with pytest.raises(StateConflictError):
        service.publish(project.id, PublishCreate(platforms=["youtube"]))


@pytest.mark.parametrize("operation", ["trim", "audio", "missing", "bulk"])
def test_failed_edits_leave_stored_timeline_unchanged(
    service, timeline_project, operation
):
    from content_factory.service import NotFoundError

    project = timeline_project
    project.video_project.aspect_ratio = "invalid"
    before = project.model_copy(deep=True)
    with pytest.raises((StateConflictError, NotFoundError)):
        if operation == "trim":
            service.trim_scene(project.id, "first", 5, 1)
        elif operation == "audio":
            service.set_scene_audio(project.id, "first", 0.2, 2, 2)
        elif operation == "missing":
            service.duplicate_video_scene(project.id, "missing")
        else:
            service.bulk_update_video_scenes(
                project.id, ["first", "second"], {"grade": "invalid"}
            )
    assert service.get_project(project.id) == before
    assert project == before


@pytest.mark.parametrize("operation", ["rebuild", "assist", "polish"])
def test_generated_edits_normalize_and_preserve_policy(
    service, timeline_project, operation
):
    project = timeline_project
    project.status = ProjectStatus.PUBLISHED
    project.video_project.aspect_ratio = "invalid"
    project.video_project.scenes[0].font_size = 1
    before = project.model_copy(deep=True)
    if operation == "rebuild":
        result = service.build_video_project(project.id)
    elif operation == "assist":
        result = service.apply_ai_assist(project.id, fit=True, beat=True, bpm=100)
    else:
        result = service.polish_scene_text(project.id, "first")
    assert result.video_project.revision == before.video_project.revision + 1
    assert result.video_project.aspect_ratio == "9:16"
    assert result.video_project.scenes[0].font_size >= 16
    assert result.status == before.status
    assert result.approvals == before.approvals
    assert result.source_rights_confirmed is False
    assert project == before


@pytest.mark.parametrize("operation", ["rebuild", "assist", "polish", "save"])
def test_normalization_failure_rolls_back_project(
    service, timeline_project, monkeypatch, operation
):
    before = timeline_project.model_copy(deep=True)

    def fail(video):
        video.scenes[0].text = "partial edit"
        raise RuntimeError("normalization failed")

    monkeypatch.setattr("content_factory.services.timeline.timeline.normalize", fail)
    with pytest.raises(RuntimeError, match="normalization failed"):
        if operation == "rebuild":
            service.build_video_project(before.id)
        elif operation == "assist":
            service.apply_ai_assist(before.id, fit=True, beat=True, bpm=100)
        elif operation == "polish":
            service.polish_scene_text(before.id, "first")
        else:
            service.update_video_project(before.id, before.video_project)
    assert service.get_project(before.id) == before


def test_save_does_not_mutate_or_retain_client_document(service, timeline_project):
    edit = timeline_project.video_project.model_copy(deep=True)
    edit.revision = 5000
    edit.aspect_ratio = "invalid"
    before = edit.model_copy(deep=True)
    result = service.update_video_project(timeline_project.id, edit)
    assert result.video_project.revision == 18
    assert edit == before
    edit.scenes[0].text = "changed after saving"
    assert service.get_project(result.id).video_project.scenes[0].text == "Hello world"


@pytest.mark.parametrize("operation", ["copy", "render"])
def test_timeline_reads_do_not_normalize_live_store(
    service, timeline_project, operation
):
    timeline_project.video_project.aspect_ratio = "invalid"
    before = timeline_project.model_copy(deep=True)
    if operation == "copy":
        service.copy_scene(before.id, "first")
    else:
        service.render_plan(before.id)
    assert service.get_project(before.id) == before


def test_timeline_report_for_api_created_project(
    client_with_template: TestClient,
) -> None:
    project_id = _drive_to_review(client_with_template)
    response = client_with_template.get(f"/projects/{project_id}/timeline/report")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["stats"]["scene_count"] >= 2
    assert 0 <= body["score"] <= 100
    assert body["target_seconds"] == 30
    assert any(issue["code"] == "flat_look" for issue in body["issues"])
    severities = {severity.value for severity in IssueSeverity}
    assert all(issue["severity"] in severities for issue in body["issues"])


def test_render_plan_endpoint(client_with_template: TestClient) -> None:
    project_id = _drive_to_review(client_with_template)
    response = client_with_template.get(f"/projects/{project_id}/render-plan")
    assert response.status_code == 200, response.text
    plan = response.json()
    assert plan["project_id"] == project_id
    assert (plan["width"], plan["height"]) == (1080, 1920)
    assert plan["fps"] == 30
    assert len(plan["steps"]) >= 2
    assert plan["total_seconds"] > 0
    assert plan["subtitles"]
    assert {layer["kind"] for layer in plan["audio"]} == {"voiceover", "music"}
    assert plan["steps"][0]["start_seconds"] == 0.0
    assert plan["steps"][0]["transition_in"] == "cut"


def test_split_merge_duplicate_delete_and_move(
    client_with_template: TestClient,
) -> None:
    project_id = _drive_to_review(client_with_template)
    original = _scene_ids(client_with_template, project_id)

    split = client_with_template.post(
        f"/projects/{project_id}/timeline/scenes/{original[0]}/split", json={"at": 0.5}
    )
    assert split.status_code == 200, split.text
    after_split = [scene["id"] for scene in split.json()["video_project"]["scenes"]]
    assert len(after_split) == len(original) + 1
    assert after_split[0] == original[0]

    merged = client_with_template.post(
        f"/projects/{project_id}/timeline/scenes/{original[0]}/merge"
    )
    assert merged.status_code == 200, merged.text
    assert len(merged.json()["video_project"]["scenes"]) == len(original)

    duplicated = client_with_template.post(
        f"/projects/{project_id}/timeline/scenes/{original[0]}/duplicate"
    )
    assert duplicated.status_code == 200, duplicated.text
    assert len(duplicated.json()["video_project"]["scenes"]) == len(original) + 1

    moved = client_with_template.post(
        f"/projects/{project_id}/timeline/scenes/{original[-1]}/move",
        json={"to_index": 0},
    )
    assert moved.status_code == 200, moved.text
    assert moved.json()["video_project"]["scenes"][0]["id"] == original[-1]

    deleted = client_with_template.delete(
        f"/projects/{project_id}/timeline/scenes/{original[-1]}"
    )
    assert deleted.status_code == 200, deleted.text
    assert all(
        scene["id"] != original[-1]
        for scene in deleted.json()["video_project"]["scenes"]
    )


def test_edits_bump_the_revision(client_with_template: TestClient) -> None:
    project_id = _drive_to_review(client_with_template)
    first = _timeline(client_with_template, project_id)["revision"]
    client_with_template.post(f"/projects/{project_id}/timeline/normalize")
    assert _timeline(client_with_template, project_id)["revision"] == first + 1


def test_revision_is_server_owned(client_with_template: TestClient) -> None:
    """A client cannot jump or reset the revision counter."""
    project_id = _drive_to_review(client_with_template)
    stored = _timeline(client_with_template, project_id)
    forged = dict(stored)
    forged["revision"] = 5000
    response = client_with_template.put(
        f"/projects/{project_id}/video-project", json={"project": forged}
    )
    assert response.status_code == 200, response.text
    assert response.json()["video_project"]["revision"] == stored["revision"] + 1

    preserved = _timeline(client_with_template, project_id)
    assert preserved["markers"] == stored["markers"]
    assert preserved["voiceover_volume"] == stored["voiceover_volume"]


def test_saving_an_unnormalized_document_repairs_it(
    client_with_template: TestClient,
) -> None:
    project_id = _drive_to_review(client_with_template)
    stored = _timeline(client_with_template, project_id)
    broken = dict(stored)
    broken["aspect_ratio"] = "42:1"
    broken["scenes"] = [dict(scene, id="dup") for scene in stored["scenes"]] + [
        {"id": "dup", "label": "Extra", "text": "hi", "duration_seconds": 1}
    ]
    response = client_with_template.put(
        f"/projects/{project_id}/video-project", json={"project": broken}
    )
    assert response.status_code == 200, response.text
    timeline = response.json()["video_project"]
    assert timeline["aspect_ratio"] == "9:16"
    ids = [scene["id"] for scene in timeline["scenes"]]
    assert len(set(ids)) == len(ids)


def test_bulk_update_endpoint(client_with_template: TestClient) -> None:
    project_id = _drive_to_review(client_with_template)
    ids = _scene_ids(client_with_template, project_id)[:2]
    response = client_with_template.post(
        f"/projects/{project_id}/timeline/scenes/bulk",
        json={"scene_ids": ids, "patch": {"grade": "noir", "font_size": 60}},
    )
    assert response.status_code == 200, response.text
    scenes = {
        scene["id"]: scene for scene in response.json()["video_project"]["scenes"]
    }
    for scene_id in ids:
        assert scenes[scene_id]["grade"] == "noir"
        assert scenes[scene_id]["font_size"] == 60


def test_bulk_update_rejects_an_empty_patch(client_with_template: TestClient) -> None:
    project_id = _drive_to_review(client_with_template)
    response = client_with_template.post(
        f"/projects/{project_id}/timeline/scenes/bulk",
        json={
            "scene_ids": [_scene_ids(client_with_template, project_id)[0]],
            "patch": {},
        },
    )
    assert response.status_code == 422, response.text


def test_marker_endpoints(client_with_template: TestClient) -> None:
    project_id = _drive_to_review(client_with_template)
    created = client_with_template.post(
        f"/projects/{project_id}/timeline/markers",
        json={"time_seconds": 2.5, "label": "beat 1", "color": "#22d3ee"},
    )
    assert created.status_code == 200, created.text
    markers = created.json()["video_project"]["markers"]
    assert len(markers) == 1
    assert markers[0]["label"] == "beat 1"
    marker_id = markers[0]["id"]

    report = client_with_template.get(f"/projects/{project_id}/timeline/report").json()
    assert report["stats"]["marker_count"] == 1
    assert not any(issue["code"] == "no_markers" for issue in report["issues"])

    removed = client_with_template.delete(
        f"/projects/{project_id}/timeline/markers/{marker_id}"
    )
    assert removed.status_code == 200, removed.text
    assert removed.json()["video_project"]["markers"] == []

    missing = client_with_template.delete(
        f"/projects/{project_id}/timeline/markers/{marker_id}"
    )
    assert missing.status_code == 404, missing.text


def test_unknown_scene_returns_404(client_with_template: TestClient) -> None:
    project_id = _drive_to_review(client_with_template)
    response = client_with_template.post(
        f"/projects/{project_id}/timeline/scenes/nope/duplicate"
    )
    assert response.status_code == 404, response.text
    assert "nope" in response.json()["detail"]


def test_timeline_edits_are_blocked_before_video_review(
    client_with_template: TestClient,
) -> None:
    created = client_with_template.post(
        "/projects",
        json={
            "name": "Draft",
            "topic": "still in draft",
            "target_language": "en",
            "duration_target_seconds": 20,
        },
    )
    project_id = created.json()["id"]
    response = client_with_template.post(f"/projects/{project_id}/timeline/normalize")
    assert response.status_code == 409, response.text
    assert "No video project" in response.json()["detail"]


def test_published_cuts_stay_editable(client_with_template: TestClient) -> None:
    project_id = _drive_to_review(client_with_template)
    client_with_template.post(
        f"/projects/{project_id}/approvals",
        json={"stage": "video", "verdict": "approved"},
    )
    published = client_with_template.post(
        f"/projects/{project_id}/publish", json={"platforms": ["youtube"]}
    )
    assert published.json()["status"] == "published"
    response = client_with_template.post(f"/projects/{project_id}/timeline/normalize")
    assert response.status_code == 200, response.text


def test_timeline_endpoints_require_a_project(client_with_template: TestClient) -> None:
    assert client_with_template.get("/projects/nope/timeline/report").status_code == 404
    assert client_with_template.get("/projects/nope/render-plan").status_code == 404
    assert (
        client_with_template.post("/projects/nope/timeline/normalize").status_code
        == 404
    )
