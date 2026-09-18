"""Tests for the HTTP API surface."""

from __future__ import annotations

import time

from fastapi.testclient import TestClient


def wait_for_status(
    client: TestClient, project_id: str, expected: str, timeout: float = 3.0
) -> dict:
    """Poll a project until it reaches ``expected`` (used for async workers)."""
    deadline = time.time() + timeout
    body: dict = {}
    while time.time() < deadline:
        body = client.get(f"/projects/{project_id}").json()
        if body["status"] == expected:
            return body
        time.sleep(0.01)
    raise AssertionError(
        f"Timed out waiting for '{expected}', got '{body.get('status')}'"
    )


def create_project(
    client: TestClient, name: str = "Demo", topic: str = "A topic"
) -> dict:
    response = client.post(
        "/projects", json={"name": name, "topic": topic, "target_language": "vi"}
    )
    assert response.status_code == 201
    return response.json()


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["app"] == "ai-content-factory"
    assert "providers" in body


def test_create_project(client: TestClient) -> None:
    body = create_project(client)
    assert body["status"] == "draft"
    assert body["id"]
    assert body["script"] is None


def test_create_project_validation(client: TestClient) -> None:
    response = client.post("/projects", json={"name": "", "topic": ""})
    assert response.status_code == 422


def test_list_projects(client: TestClient) -> None:
    create_project(client, name="A")
    create_project(client, name="B")
    response = client.get("/projects")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_project_not_found(client: TestClient) -> None:
    assert client.get("/projects/nope").status_code == 404


def test_script_approval_lifecycle_over_http(client: TestClient) -> None:
    created = create_project(client)

    updated = client.put(
        f"/projects/{created['id']}/script",
        json={"script": "Final narration.", "source_rights_confirmed": True},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "script_review"

    approved = client.post(
        f"/projects/{created['id']}/approvals",
        json={"stage": "script", "verdict": "approved", "comment": "Looks good"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "script_approved"
    assert approved.json()["approvals"][0]["verdict"] == "approved"

    generating = client.post(f"/projects/{created['id']}/generate")
    assert generating.status_code == 200
    assert generating.json()["status"] == "generating"


def test_generate_script_degrades_when_no_providers(client: TestClient) -> None:
    created = create_project(client)
    response = client.post(f"/projects/{created['id']}/script/generate")
    assert response.status_code == 503


def test_generate_script_with_template(client_with_template: TestClient) -> None:
    created = create_project(client_with_template)
    response = client_with_template.post(f"/projects/{created['id']}/script/generate")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "script_review"
    assert body["script"]
    assert body["source_rights_confirmed"] is False
    assert body["provider_used"] == "template"
    assert body["research"] is not None
    assert body["research"]["sources"]
    assert body["research"]["key_facts"]


def test_research_endpoint(client: TestClient) -> None:
    created = create_project(client)
    response = client.post(f"/projects/{created['id']}/research")
    assert response.status_code == 200
    body = response.json()
    assert body["research"] is not None
    assert len(body["research"]["sources"]) >= 2
    assert body["status"] == "draft"


def test_get_research_not_run_yet(client: TestClient) -> None:
    created = create_project(client)
    assert client.get(f"/projects/{created['id']}/research").status_code == 404


def test_get_research_after_run(client: TestClient) -> None:
    created = create_project(client)
    client.post(f"/projects/{created['id']}/research")
    response = client.get(f"/projects/{created['id']}/research")
    assert response.status_code == 200
    assert response.json()["sources"]


def test_approve_requires_rights(client: TestClient) -> None:
    created = create_project(client)
    client.put(f"/projects/{created['id']}/script", json={"script": "Text"})
    response = client.post(
        f"/projects/{created['id']}/approvals",
        json={"stage": "script", "verdict": "approved"},
    )
    assert response.status_code == 409


def test_generate_blocked_before_approval(client: TestClient) -> None:
    created = create_project(client)
    assert client.post(f"/projects/{created['id']}/generate").status_code == 409


def test_edit_script_blocked_after_approval(client: TestClient) -> None:
    created = create_project(client)
    client.put(
        f"/projects/{created['id']}/script",
        json={"script": "Text", "source_rights_confirmed": True},
    )
    client.post(
        f"/projects/{created['id']}/approvals",
        json={"stage": "script", "verdict": "approved"},
    )
    response = client.put(
        f"/projects/{created['id']}/script", json={"script": "Edited"}
    )
    assert response.status_code == 409


def test_full_pipeline_to_published(client: TestClient) -> None:
    created = create_project(client)
    pid = created["id"]

    client.put(
        f"/projects/{pid}/script",
        json={"script": "Final narration.", "source_rights_confirmed": True},
    )
    client.post(
        f"/projects/{pid}/approvals",
        json={"stage": "script", "verdict": "approved"},
    )
    assert client.post(f"/projects/{pid}/generate").json()["status"] == "generating"

    reviewed = wait_for_status(client, pid, "video_review")
    assert reviewed["video"] is not None
    assert reviewed["progress"] == 100

    approved = client.post(
        f"/projects/{pid}/approvals",
        json={"stage": "video", "verdict": "approved", "comment": "Ship it"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "video_approved"

    published = client.post(f"/projects/{pid}/publish", json={"platforms": ["youtube"]})
    assert published.status_code == 200
    assert published.json()["status"] == "published"
    assert published.json()["platforms"] == ["youtube"]
    assert published.json()["published_at"] is not None


def test_publish_blocked_before_video_approval(client: TestClient) -> None:
    created = create_project(client)
    assert (
        client.post(
            f"/projects/{created['id']}/publish", json={"platforms": ["youtube"]}
        ).status_code
        == 409
    )


def test_video_approval_blocked_before_production(client: TestClient) -> None:
    created = create_project(client)
    response = client.post(
        f"/projects/{created['id']}/approvals",
        json={"stage": "video", "verdict": "approved"},
    )
    assert response.status_code == 409


def test_thumbnail_endpoint(client: TestClient) -> None:
    created = create_project(client)
    pid = created["id"]
    client.put(
        f"/projects/{pid}/script",
        json={"script": "Final narration.", "source_rights_confirmed": True},
    )
    client.post(
        f"/projects/{pid}/approvals", json={"stage": "script", "verdict": "approved"}
    )
    client.post(f"/projects/{pid}/generate")
    wait_for_status(client, pid, "video_review")

    response = client.get(f"/projects/{pid}/thumbnail")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/svg+xml"
    assert "Demo" in response.text


def test_frontend_is_served(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "AI Content Factory" in response.text


def test_frontend_assets_are_served(client: TestClient) -> None:
    assert client.get("/assets/app.js").status_code == 200
    assert client.get("/assets/style.css").status_code == 200


def test_documents_search_offline_returns_empty(client: TestClient) -> None:
    response = client.get("/documents/search", params={"q": "morning light"})
    assert response.status_code == 200
    assert response.json() == []


def test_add_document_downloads_and_attaches(client: TestClient) -> None:
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    import pymupdf

    pdf = pymupdf.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "Morning light resets the circadian clock.")
    payload = pdf.tobytes()
    pdf.close()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args) -> None:  # noqa: ANN002
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        created = create_project(client)
        result = {
            "id": "arxiv:1234.5678",
            "title": "Attached Paper",
            "authors": ["Jane Doe"],
            "year": 2024,
            "abstract": "A study about morning light.",
            "source": "arxiv",
            "pdf_url": f"http://127.0.0.1:{port}/paper.pdf",
            "landing_url": f"http://127.0.0.1:{port}/paper",
            "is_open_access": True,
        }
        response = client.post(f"/projects/{created['id']}/documents", json=result)
        assert response.status_code == 200
        body = response.json()
        assert len(body["documents"]) == 1
        assert body["documents"][0]["title"] == "Attached Paper"
        assert body["documents"][0]["source"] == "arxiv"
    finally:
        server.shutdown()
        server.server_close()


def test_add_document_fails_on_bad_url(client: TestClient) -> None:
    created = create_project(client)
    result = {
        "id": "x:1",
        "title": "Broken Paper",
        "source": "test",
        "pdf_url": "http://127.0.0.1:1/unreachable.pdf",
    }
    response = client.post(f"/projects/{created['id']}/documents", json=result)
    assert response.status_code == 502


def test_library_endpoints(client: TestClient) -> None:
    response = client.get("/library")
    assert response.status_code == 200
    body = response.json()
    assert body["stats"]["documents"] == 0
    assert client.get("/library/search", params={"q": "nothing"}).json() == []
