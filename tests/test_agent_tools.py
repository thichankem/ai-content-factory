"""Tests for the agent tool registry (manifest + dispatch + endpoints)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from content_factory.agent_tools import TOOL_MANIFEST, ToolError, dispatch_tool
from content_factory.api import create_app
from content_factory.config import Settings
from content_factory.models import ProjectCreate


@pytest.fixture
def service(tmp_path):
    settings = Settings(
        store_path=str(tmp_path / "projects.json"),
        uploads_dir=str(tmp_path / "uploads"),
    )
    from content_factory.service import ContentFactoryService

    return ContentFactoryService(settings)


@pytest.fixture
def client(tmp_path) -> TestClient:
    settings = Settings(
        store_path=str(tmp_path / "projects.json"),
        uploads_dir=str(tmp_path / "uploads"),
    )
    return TestClient(create_app(settings))


@pytest.fixture
def project_id(service) -> str:
    return service.create_project(
        ProjectCreate(name="Tool demo", topic="Lịch sử tàu Titanic")
    ).id


# --- Manifest ---------------------------------------------------------------


def test_manifest_names_are_unique_and_documented() -> None:
    names = [tool["name"] for tool in TOOL_MANIFEST]
    assert len(names) == len(set(names))
    assert len(names) >= 25
    for tool in TOOL_MANIFEST:
        assert tool["description"], tool["name"]
        assert tool["service"], tool["name"]
        assert tool["category"] in {
            "discovery",
            "research",
            "script",
            "timeline",
            "production",
            "image",
            "voice",
            "media",
            "audio",
            "seo",
        }
        assert tool["input_schema"]["type"] == "object"


def test_manifest_lists_the_seo_tools() -> None:
    names = {tool["name"] for tool in TOOL_MANIFEST}
    assert {
        "seo_rules",
        "seo_score",
        "seo_optimize",
        "seo_score_project",
        "seo_ab_plan",
        "seo_ab_evaluate",
        "seo_keywords",
        "seo_calibrate",
    } <= names


def test_manifest_lists_the_nle_tools() -> None:
    names = {tool["name"] for tool in TOOL_MANIFEST}
    assert {
        "set_scene_speed",
        "reverse_scene",
        "trim_scene",
        "set_scene_audio",
        "split_scene",
        "merge_scene",
        "render_plan",
        "ground_project",
    } <= names


# --- Dispatch ----------------------------------------------------------------


def test_dispatch_list_projects_returns_json(service, project_id) -> None:
    result = dispatch_tool(service, "list_projects", {})
    assert isinstance(result, list)
    assert any(item["id"] == project_id for item in result)


def test_dispatch_update_script_sets_rights_flag(service, project_id) -> None:
    dispatch_tool(
        service,
        "update_script",
        {
            "project_id": project_id,
            "script": "[Hook]\nX.\n\n[Outro]\nY.",
            "source_rights_confirmed": True,
        },
    )
    project = dispatch_tool(service, "get_project", {"project_id": project_id})
    assert project["source_rights_confirmed"] is True


def test_dispatch_unknown_tool_raises(service) -> None:
    with pytest.raises(ToolError, match="Unknown tool"):
        dispatch_tool(service, "does_not_exist", {})


def test_dispatch_missing_required_argument(service) -> None:
    with pytest.raises(ToolError, match="Missing required"):
        dispatch_tool(service, "get_project", {})


def test_dispatch_rejects_malformed_ids(service) -> None:
    with pytest.raises(ToolError, match="project_id"):
        dispatch_tool(service, "get_project", {"project_id": "with spaces!"})


def test_dispatch_full_script_flow(service, project_id) -> None:
    script = (
        "[Hook]\nCon tàu được cho là không thể chìm.\n\n"
        "[Outro]\nLịch sử dạy chúng ta khiêm tốn."
    )
    dispatch_tool(
        service,
        "update_script",
        {
            "project_id": project_id,
            "script": script,
            "source_rights_confirmed": True,
        },
    )
    dispatch_tool(
        service,
        "approve_stage",
        {"project_id": project_id, "stage": "script", "verdict": "approved"},
    )
    result = dispatch_tool(service, "build_video_project", {"project_id": project_id})
    assert result["video_project"]["scenes"], "expected scenes after build"


def test_dispatch_timeline_edits(service, project_id) -> None:
    script = "[Hook]\nMột giây.\n\n[Outro]\nKết."
    dispatch_tool(
        service,
        "update_script",
        {
            "project_id": project_id,
            "script": script,
            "source_rights_confirmed": True,
        },
    )
    dispatch_tool(
        service,
        "approve_stage",
        {"project_id": project_id, "stage": "script", "verdict": "approved"},
    )
    result = dispatch_tool(service, "build_video_project", {"project_id": project_id})
    service.produce_video(project_id)
    result = dispatch_tool(service, "get_project", {"project_id": project_id})
    scenes = result["video_project"]["scenes"]
    sid = scenes[0]["id"]

    sped = dispatch_tool(
        service,
        "set_scene_speed",
        {"project_id": project_id, "scene_id": sid, "speed": 0.5},
    )
    assert sped["video_project"]["scenes"][0]["speed"] == 0.5

    reversed_project = dispatch_tool(
        service,
        "reverse_scene",
        {"project_id": project_id, "scene_id": sid, "reverse": True},
    )
    assert reversed_project["video_project"]["scenes"][0]["reverse"] is True

    trimmed = dispatch_tool(
        service,
        "trim_scene",
        {"project_id": project_id, "scene_id": sid, "trim_start": 1.0, "trim_end": 3.0},
    )
    assert trimmed["video_project"]["scenes"][0]["trim_start"] == 1.0

    audio = dispatch_tool(
        service,
        "set_scene_audio",
        {"project_id": project_id, "scene_id": sid, "volume": 0.5, "fade_in": 0.5},
    )
    assert audio["video_project"]["scenes"][0]["volume"] == 0.5


# --- SEO tools ----------------------------------------------------------------


def _demo_pack(**overrides) -> dict:
    """A middling pack: real but unoptimised, the state most creators ship in."""
    pack = {
        "title": "Tàu Titanic",
        "description": "Chuyện con tàu.",
        "keywords": ["tàu titanic"],
        "aspect_ratio": "16:9",
        "duration_seconds": 240.0,
        "has_captions": True,
        "hook": "Con tàu này được cho là không thể chìm.",
    }
    pack.update(overrides)
    return pack


def test_dispatch_seo_rules_lists_every_platform(service) -> None:
    rules = dispatch_tool(service, "seo_rules", {})
    keys = {row["platform"] for row in rules}
    assert {"youtube", "youtube_shorts", "tiktok"} <= keys
    assert all(row["dimensions"] and row["signals"] for row in rules)


def test_dispatch_seo_score_ranks_a_good_pack_above_a_bad_one(service) -> None:
    thin = dispatch_tool(service, "seo_score", {"platform": "youtube", "pack": {}})
    full = dispatch_tool(
        service,
        "seo_score",
        {
            "platform": "youtube",
            "pack": _demo_pack(
                tags=["titanic", "lịch sử"],
                hashtags=["#titanic", "#lichsu", "#khampha"],
                has_chapters=True,
                chapter_count=4,
                thumbnail_present=True,
            ),
        },
    )
    assert full["score"] > thin["score"]
    assert full["dimensions"] and thin["grade"] == "F"


def test_dispatch_seo_score_all_returns_both_platforms(service) -> None:
    result = dispatch_tool(
        service, "seo_score", {"platform": "all", "pack": _demo_pack()}
    )
    assert {"youtube", "tiktok"} <= set(result)
    assert 0 <= result["tiktok"]["score"] <= 100


def test_dispatch_seo_optimize_reports_a_measured_gain(service) -> None:
    plan = dispatch_tool(
        service, "seo_optimize", {"platform": "tiktok", "pack": _demo_pack()}
    )
    assert plan["gain"] >= 0
    assert plan["after"]["score"] >= plan["before"]["score"]
    assert plan["projected_score"] == plan["after"]["score"]
    assert plan["changes"], "the rewrite must explain itself"


def test_dispatch_seo_score_project_reads_the_real_timeline(
    service, project_id
) -> None:
    dispatch_tool(
        service,
        "update_script",
        {
            "project_id": project_id,
            "script": "[Hook]\nCon tàu không thể chìm.\n\n[Outro]\nKết.",
            "source_rights_confirmed": True,
        },
    )
    dispatch_tool(
        service,
        "approve_stage",
        {"project_id": project_id, "stage": "script", "verdict": "approved"},
    )
    dispatch_tool(service, "build_video_project", {"project_id": project_id})
    report = dispatch_tool(
        service, "seo_score_project", {"project_id": project_id, "platform": "all"}
    )
    assert report["project_id"] == project_id
    assert set(report["platforms"]) >= {"youtube", "tiktok"}
    youtube = report["platforms"]["youtube"]
    assert youtube["score"] >= 0
    assert youtube["metrics"]["title_chars"] > 0
    # The hook is read from the stored script, not passed in by the caller.
    assert report["pack_used"]["hook"].startswith("Con tàu")


def test_dispatch_seo_ab_plan_sizes_the_test(service) -> None:
    plan = dispatch_tool(
        service,
        "seo_ab_plan",
        {"metric": "ctr", "baseline_rate": 0.04, "daily_traffic": 5000},
    )
    assert plan["per_arm"] > 0
    assert plan["total"] == plan["per_arm"] * 2
    assert plan["days"] > 0
    assert plan["decision_rule"]


def test_dispatch_seo_ab_evaluate_calls_a_real_winner(service) -> None:
    result = dispatch_tool(
        service,
        "seo_ab_evaluate",
        {
            "metric": "ctr",
            "arms": [
                {"name": "control", "impressions": 40000, "clicks": 1600},
                {"name": "variant_b", "impressions": 40000, "clicks": 2200},
            ],
        },
    )
    assert result["winner"] == "variant_b"
    assert result["p_value"] < 0.05
    assert result["lift_relative"] > 0


def test_dispatch_seo_ab_evaluate_rejects_a_single_arm(service) -> None:
    with pytest.raises(ToolError, match="at least two"):
        dispatch_tool(
            service,
            "seo_ab_evaluate",
            {"arms": [{"name": "only", "impressions": 10, "clicks": 1}]},
        )


def test_dispatch_seo_keywords_ranks_phrases(service) -> None:
    result = dispatch_tool(
        service,
        "seo_keywords",
        {
            "keywords": ["tàu titanic", "thảm hoạ hàng hải"],
            "competitors": [
                {"title": "Tàu Titanic chìm", "views": 120000, "subscribers": 5000},
                {"title": "Bí ẩn Titanic", "views": 80000, "subscribers": 900},
            ],
        },
    )
    assert result["rows"]
    assert all(row["keyword"] for row in result["rows"])


def test_dispatch_seo_keywords_needs_a_phrase(service) -> None:
    with pytest.raises(ToolError, match="keywords"):
        dispatch_tool(service, "seo_keywords", {"keywords": []})


def test_dispatch_seo_calibrate_learns_from_own_numbers(service) -> None:
    result = dispatch_tool(
        service,
        "seo_calibrate",
        {
            "platform": "youtube",
            "observations": [
                {"signals": {"hook_strength": 40, "packaging": 30}, "outcome": 900},
                {"signals": {"hook_strength": 70, "packaging": 60}, "outcome": 2600},
                {"signals": {"hook_strength": 90, "packaging": 85}, "outcome": 5400},
            ],
        },
    )
    assert result["observations"] == 3
    assert result["correlations"], "calibration should report per-signal evidence"


def test_dispatch_seo_rejects_an_unknown_platform(service) -> None:
    with pytest.raises(ToolError, match="platform"):
        dispatch_tool(service, "seo_score", {"platform": "myspace", "pack": {}})


def test_dispatch_seo_requires_a_pack(service) -> None:
    with pytest.raises(ToolError, match="Missing required"):
        dispatch_tool(service, "seo_score", {"platform": "youtube"})


# --- HTTP endpoints -----------------------------------------------------------


def test_tools_endpoint_returns_manifest(client) -> None:
    response = client.get("/tools")
    assert response.status_code == 200
    body = response.json()
    assert body["protocol"] == "content-factory-tools/1"
    assert body["count"] >= 25


def test_tools_call_roundtrip(client) -> None:
    created = client.post(
        "/projects", json={"name": "Via tools", "topic": "Núi lửa Krakatoa"}
    )
    project_id = created.json()["id"]
    response = client.post(
        "/tools/call", json={"tool": "get_project", "args": {"project_id": project_id}}
    )
    assert response.status_code == 200
    assert response.json()["id"] == project_id


def test_tools_call_unknown_tool_maps_to_422(client) -> None:
    response = client.post("/tools/call", json={"tool": "nope", "args": {}})
    assert response.status_code == 422


def test_tools_call_domain_error_maps_to_404(client) -> None:
    response = client.post(
        "/tools/call", json={"tool": "get_project", "args": {"project_id": "missing"}}
    )
    assert response.status_code == 404
