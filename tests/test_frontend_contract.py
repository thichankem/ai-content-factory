"""The HTTP contract the web clients depend on, pinned field by field.

The studio (``frontend/src``) and the legacy dashboard (``frontend/app.js``)
read specific names out of specific responses. Those names are a contract, and
the failure mode when one drifts is silent: a ``NaN`` width, a script editor
that falls back to its placeholder, a cost card that always reads $0.00. None of
that raises, so no ordinary unit test notices.

This module therefore drives the real pipeline over HTTP with the *exact*
payloads the clients send, and asserts the *exact* fields they read. It is the
executable definition of "the backend serves the frontend".
"""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from content_factory.api import create_app
from content_factory.config import Settings

#: Payloads below are copied from the client code, comments and all, so a change
#: there without a change here shows up as a failure rather than a runtime 422.


@pytest.fixture
def client(settings: Settings) -> TestClient:
    """Client with the built-in template enabled, so a pipeline can run offline."""
    enabled = settings.model_copy(update={"template_enabled": True})
    return TestClient(create_app(enabled))


def _create(client: TestClient) -> str:
    response = client.post(
        "/projects",
        json={
            "name": "Contract",
            "topic": "Why morning light changes how a city feels",
            "target_language": "vi",
            "duration_target_seconds": 45,
        },
    )
    assert response.status_code < 300, response.text
    return response.json()["id"]


def _save_script(client: TestClient, project_id: str) -> None:
    """Save a script the way the studio does, then clear rights."""
    response = client.put(
        f"/projects/{project_id}/script",
        json={
            "raw_script": (
                "[Hook]\nXin chao cac ban.\n\n"
                "[Turn]\nDay la phan than cua cau chuyen.\n\n"
                "[CTA]\nTheo doi minh nhe."
            ),
            "source_rights_confirmed": True,
        },
    )
    assert response.status_code < 300, response.text


def _approve_and_generate(client: TestClient, project_id: str) -> dict:
    """Walk GATE 1, start the worker, and wait for an editable timeline."""
    approved = client.post(
        f"/projects/{project_id}/approvals",
        json={"stage": "script", "verdict": "approved", "comment": "contract"},
    )
    assert approved.status_code < 300, approved.text
    assert approved.json()["status"] == "script_approved"

    started = client.post(f"/projects/{project_id}/generate")
    assert started.status_code < 300, started.text
    assert started.json()["status"] == "generating"

    deadline = time.monotonic() + 30.0
    while time.monotonic() < deadline:
        project = client.get(f"/projects/{project_id}").json()
        if project["status"] in {"video_review", "video_approved", "published"}:
            return project
        time.sleep(0.05)
    raise AssertionError("generation did not finish within 30s")


def _missing(payload: dict, fields: tuple[str, ...]) -> list[str]:
    return [field for field in fields if field not in payload]


def test_script_studio_reads_script_document(client: TestClient) -> None:
    """The editor binds to ``script_document``; ``script`` stays raw text.

    Both are needed: the renderer, the CLI and the legacy dashboard read the raw
    text, while the editor's section list and style selector need the bundle.
    """
    project_id = _create(client)
    _save_script(client, project_id)
    project = client.get(f"/projects/{project_id}").json()

    assert isinstance(project["script"], str)
    document = project["script_document"]
    assert not _missing(
        document, ("topic", "style", "raw_script", "sections", "timing_plan")
    )
    assert document["raw_script"] == project["script"]

    section = document["sections"][0]
    # Both spellings, because the pipeline and the editor name these differently.
    assert not _missing(
        section,
        ("name", "text", "duration_target_seconds", "label", "unit_count"),
    )
    assert section["name"] == section["label"]
    assert document["timing_plan"]["total_duration"] == pytest.approx(
        document["timing_plan"]["estimated_seconds"]
    )


def test_virality_scores_carry_every_axis(client: TestClient) -> None:
    response = client.post(
        "/script/virality",
        json={"script_text": "[Hook]\nXin chao cac ban.", "topic": "morning light"},
    )
    assert response.status_code == 200
    assert not _missing(
        response.json(),
        (
            "score",
            "hook_score",
            "pacing_score",
            "duration_score",
            "cta_score",
            "advice",
        ),
    )


def test_agent_catalog_serves_both_audiences(client: TestClient) -> None:
    """``/agents`` is read by the pipeline and rendered by the studio."""
    response = client.get("/agents")
    assert response.status_code == 200
    catalog = response.json()
    assert not _missing(catalog, ("agents", "script_styles", "tts_voices"))

    if catalog["agents"]:
        assert not _missing(
            catalog["agents"][0],
            ("id", "name", "role", "provider", "enabled", "model", "capabilities"),
        )
    assert not _missing(catalog["script_styles"][0], ("id", "name", "description"))
    voice = catalog["tts_voices"][0]
    assert not _missing(voice, ("id", "name", "language", "gender"))
    # A picker must not offer a voice the engine cannot actually speak.
    assert voice["id"].endswith("Neural")


def test_agent_result_accepts_the_studio_spelling(client: TestClient) -> None:
    project_id = _create(client)
    response = client.post(
        f"/projects/{project_id}/agent-result",
        json={"markdown_response": "## Script\n[Hook]\nXin chao cac ban."},
    )
    assert response.status_code < 300, response.text
    assert response.json()["script"]


def test_qa_verdicts_are_bindable(client: TestClient) -> None:
    platform = client.post(
        "/qa/platform/verdict",
        json={"platform": "tiktok", "duration_seconds": 30, "aspect_ratio": "9:16"},
    )
    assert platform.status_code == 200
    assert not _missing(
        platform.json(), ("platform", "passed", "issues", "recommendations")
    )

    brand = client.post(
        "/qa/brand/verdict",
        json={"font": "Inter", "primary_color": "#111111", "tone": "casual"},
    )
    assert brand.status_code == 200
    assert not _missing(brand.json(), ("passed", "findings"))

    # An empty tick-list is a state the UI itself produces, so it must answer.
    copyright_check = client.post("/qa/copyright/verdict", json={"asset_ids": []})
    assert copyright_check.status_code == 200
    body = copyright_check.json()
    assert not _missing(body, ("passed", "fingerprints"))
    assert body["checked"] == 0
    assert body["passed"] is True


def test_cost_check_answers_both_spellings(client: TestClient) -> None:
    """The studio sends ``estimated_usage``; the pipeline sends ``calls``."""
    response = client.post("/cost/check", json={"estimated_usage": {"tts": 10}})
    assert response.status_code == 200
    body = response.json()
    assert not _missing(
        body, ("within_budget", "estimated_cost", "budget_limit", "by_service")
    )
    # Reading the wrong spelling used to yield a confident $0.00 estimate.
    assert body["estimated_cost"] > 0

    canonical = client.post("/cost/check", json={"calls": {"tts": 10}})
    assert canonical.json()["estimated_cost"] == body["estimated_cost"]


def test_dedup_without_a_body_sweeps_the_library(client: TestClient) -> None:
    response = client.post("/media/dedup")
    assert response.status_code == 200
    assert not _missing(response.json(), ("duplicates", "groups", "count", "checked"))


def test_seo_plan_without_traffic_still_answers(client: TestClient) -> None:
    """No ``daily_traffic`` means no duration estimate — not a 500."""
    response = client.post(
        "/seo/ab/plan", json={"metric": "ctr", "baseline_rate": 0.05}
    )
    assert response.status_code == 200
    body = response.json()
    assert not _missing(
        body,
        (
            "metric",
            "sample_size_per_arm",
            "total_sample_size",
            "estimated_days",
            "minimum_detectable_effect",
            "decision_rule",
        ),
    )
    assert body["days"] is None
    assert body["estimated_days"] == 0


def test_timeline_scenes_and_markers_nest_the_client_names(client: TestClient) -> None:
    """The timeline renderer reads ``duration``/``id``/``time``/``label``."""
    project_id = _create(client)
    _save_script(client, project_id)
    project = _approve_and_generate(client, project_id)

    video_project = client.get(f"/projects/{project_id}/video-project").json()
    assert video_project["scenes"], "a generated project must have editable scenes"
    scene = video_project["scenes"][0]
    # `duration` and `duration_seconds` must agree: the renderer sizes clips with
    # one and the planner lays them out with the other.
    assert not _missing(scene, ("index", "label", "duration", "duration_seconds"))
    assert scene["duration"] == pytest.approx(scene["duration_seconds"])

    # editor.js posts `time_seconds`; app.js renders `item.time` back out.
    marker = client.post(
        f"/projects/{project_id}/timeline/markers",
        json={"time_seconds": 1.0, "label": "Beat", "color": "#22d3ee"},
    )
    assert marker.status_code < 300, marker.text
    markers = marker.json()["video_project"]["markers"]
    assert markers, "the marker just added must be returned"
    assert not _missing(markers[0], ("id", "time", "time_seconds", "label"))
    assert markers[0]["time"] == pytest.approx(markers[0]["time_seconds"])
    assert project["video_project"] is not None


def test_nl_command_accepts_command_and_returns_parsed_command(
    client: TestClient,
) -> None:
    project_id = _create(client)
    _save_script(client, project_id)
    _approve_and_generate(client, project_id)
    video_project = client.get(f"/projects/{project_id}/video-project").json()

    response = client.post(
        "/timeline/command",
        json={"command": "cat scene 1 thanh 3 giay", "project": video_project},
    )
    assert response.status_code < 300, response.text
    body = response.json()
    assert not _missing(body, ("parsed_command", "project", "message"))
    assert body["parsed_command"]["intent"]
    assert body["parsed_command"] is not None


def test_timeline_can_be_saved_by_both_client_urls(client: TestClient) -> None:
    """``/video-project`` takes a wrapper; ``/timeline`` takes the bare project."""
    project_id = _create(client)
    _save_script(client, project_id)
    _approve_and_generate(client, project_id)
    video_project = client.get(f"/projects/{project_id}/video-project").json()

    bare = client.put(f"/projects/{project_id}/timeline", json=video_project)
    assert bare.status_code < 300, bare.text
    assert bare.json()["video_project"] is not None

    wrapped = client.put(
        f"/projects/{project_id}/video-project", json={"project": video_project}
    )
    assert wrapped.status_code < 300, wrapped.text
    assert wrapped.json()["video_project"] is not None
