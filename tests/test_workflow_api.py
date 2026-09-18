"""HTTP tests for the drag-and-drop flow endpoints."""

from __future__ import annotations

import time

from fastapi.testclient import TestClient

SCRIPT = (
    "[Hook]\nThe library at midnight has a sound of its own.\n\n"
    "[Turn]\nPages breathe, chairs settle, the clock keeps score.\n\n"
    "[Payoff]\nStay past closing and the building starts talking."
)


def _project(client: TestClient) -> str:
    created = client.post(
        "/projects",
        json={
            "name": "Flow API",
            "topic": "A library at midnight",
            "target_language": "en",
            "duration_target_seconds": 30,
        },
    )
    assert created.status_code == 201, created.text
    return created.json()["id"]


def _approve_script(client: TestClient, project_id: str) -> None:
    client.put(
        f"/projects/{project_id}/script",
        json={"script": SCRIPT, "source_rights_confirmed": True},
    )
    client.post(
        f"/projects/{project_id}/approvals",
        json={"stage": "script", "verdict": "approved"},
    )


def _one_block_flow(block_type: str, label: str = "Block") -> dict:
    return {
        "workflow": {
            "name": "Test flow",
            "nodes": [{"id": "n1", "type": block_type, "label": label, "x": 0, "y": 0}],
            "edges": [],
            "version": 1,
        }
    }


def test_block_palette_lists_the_whole_board(client: TestClient) -> None:
    response = client.get("/workflow/blocks")
    assert response.status_code == 200
    palette = response.json()
    types = {entry["type"] for entry in palette}
    assert {"research", "script", "gate", "scenes", "voiceover", "publish"} <= types
    assert all(entry["icon"] and entry["label"] for entry in palette)


def test_get_workflow_returns_the_default_board(client: TestClient) -> None:
    project_id = _project(client)
    response = client.get(f"/projects/{project_id}/workflow")
    assert response.status_code == 200
    flow = response.json()
    assert flow["version"] == 1
    assert flow["nodes"][0]["type"] == "research"
    assert len(flow["edges"]) == len(flow["nodes"]) - 1


def test_default_board_passes_its_own_checklist(client: TestClient) -> None:
    project_id = _project(client)
    response = client.get(f"/projects/{project_id}/workflow/checklist")
    assert response.status_code == 200
    checklist = response.json()
    assert checklist["ready"] is True
    assert checklist["issues"] == []
    assert checklist["node_count"] == 9
    assert len(checklist["order"]) == 9


def test_candidate_flow_can_be_audited_without_saving(client: TestClient) -> None:
    """The canvas audits unsaved edits, so the audit must not persist them."""
    project_id = _project(client)
    candidate = {
        "workflow": {
            "name": "Work in progress",
            "nodes": [
                {"id": "n1", "type": "research", "label": "Research"},
                {"id": "n2", "type": "gate", "label": "Review", "params": {}},
            ],
            "edges": [],
            "version": 1,
        }
    }
    response = client.post(f"/projects/{project_id}/workflow/checklist", json=candidate)
    assert response.status_code == 200, response.text
    checklist = response.json()
    assert checklist["ready"] is False
    codes = {issue["code"] for issue in checklist["issues"]}
    assert "missing_param" in codes
    assert "unconnected_block" in codes

    # The candidate flow was audited, not saved.
    stored = client.get(f"/projects/{project_id}/workflow").json()
    assert stored["name"] == "Production pipeline"
    assert len(stored["nodes"]) == 9


def test_saving_an_unfinished_board_returns_the_checklist(
    client: TestClient,
) -> None:
    project_id = _project(client)
    broken = {
        "workflow": {
            "name": "Broken",
            "nodes": [
                {"id": "n1", "type": "gate", "label": "Review me", "x": 0, "y": 0}
            ],
            "edges": [],
            "version": 1,
        }
    }
    response = client.put(f"/projects/{project_id}/workflow", json=broken)
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "stage" in detail["message"]
    assert detail["checklist"]["ready"] is False
    assert any(
        issue["code"] == "missing_param" for issue in detail["checklist"]["issues"]
    )


def test_saving_with_force_accepts_an_unfinished_board(client: TestClient) -> None:
    project_id = _project(client)
    payload = _one_block_flow("lint")
    payload["force"] = True
    response = client.put(f"/projects/{project_id}/workflow", json=payload)
    assert response.status_code == 200, response.text
    project = response.json()
    assert project["workflow"]["version"] == 1
    assert [node["type"] for node in project["workflow"]["nodes"]] == ["lint"]


def test_saving_a_board_drops_links_to_missing_blocks(client: TestClient) -> None:
    project_id = _project(client)
    payload = {
        "workflow": {
            "name": "Orphan",
            "nodes": [{"id": "n1", "type": "research", "label": "Research"}],
            "edges": [{"id": "e1", "source": "n1", "target": "gone"}],
            "version": 3,
        }
    }
    response = client.put(f"/projects/{project_id}/workflow", json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["workflow"]["edges"] == []


def test_run_stops_at_the_script_gate_using_the_stored_board(
    client_with_template: TestClient,
) -> None:
    client = client_with_template
    project_id = _project(client)
    payload = _one_block_flow("gate")
    payload["workflow"]["nodes"][0]["params"] = {"stage": "script"}
    assert (
        client.put(f"/projects/{project_id}/workflow", json=payload).status_code == 200
    )

    response = client.post(f"/projects/{project_id}/workflow/run", json={"inputs": {}})
    assert response.status_code == 200, response.text
    run = response.json()
    assert run["status"] == "blocked"
    assert run["steps"][0]["type"] == "gate"
    assert "script gate" in run["steps"][0]["error"]


def test_run_can_be_polled_in_the_background(client_with_template: TestClient) -> None:
    client = client_with_template
    project_id = _project(client)
    payload = _one_block_flow("gate")
    payload["workflow"]["nodes"][0]["params"] = {"stage": "script"}
    client.put(f"/projects/{project_id}/workflow", json=payload)

    started = client.post(
        f"/projects/{project_id}/workflow/run?background=true", json={"inputs": {}}
    )
    assert started.status_code == 200, started.text
    run_id = started.json()["id"]
    for _ in range(200):
        run = client.get(f"/workflow/runs/{run_id}").json()
        if run["status"] != "running":
            break
        time.sleep(0.02)
    assert run["status"] == "blocked"

    listed = client.get(f"/projects/{project_id}/workflow/runs").json()
    assert listed[0]["id"] == run_id


def test_run_executes_async_blocks_over_http(client_with_template: TestClient) -> None:
    """A run must survive the request's own event loop.

    The block runner drives async pipeline steps with asyncio.run(), which
    raises inside a live loop; the endpoint therefore hands the run to a thread.
    """
    client = client_with_template
    project_id = _project(client)
    payload = _one_block_flow("research")
    payload["force"] = True
    assert (
        client.put(f"/projects/{project_id}/workflow", json=payload).status_code == 200
    )

    response = client.post(f"/projects/{project_id}/workflow/run", json={"inputs": {}})
    assert response.status_code == 200, response.text
    run = response.json()
    assert run["status"] == "ok", run["steps"]
    step = run["steps"][0]
    assert step["status"] == "ok"
    assert step["output"]["sources"] >= 1


def test_unknown_run_is_a_404(client: TestClient) -> None:
    assert client.get("/workflow/runs/nope").status_code == 404


def test_workflow_endpoints_need_a_real_project(client: TestClient) -> None:
    assert client.get("/projects/ghost/workflow").status_code == 404
    assert client.get("/projects/ghost/workflow/checklist").status_code == 404
    assert (
        client.post("/projects/ghost/workflow/run", json={"inputs": {}}).status_code
        == 404
    )
