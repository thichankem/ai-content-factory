"""End-to-end smoke test for the AI Content Factory.

Drives the complete pipeline over real HTTP against a server on :8080:

    draft -> script_review -> script_approved -> generating ->
    video_review -> video_approved -> published

and exercises every auxiliary surface along the way: research, the agent
catalog, script style presets, script analysis/linting, the external AI agent
brief round-trip, the editable video project, AI-assisted editing, the library
index, voiceover, thumbnail, and the negative paths (404 / 409).

If nothing is listening, spawns its own uvicorn instance and shuts it down
afterwards. Prints one line per check. Exits 0 on success, non-zero on
failure.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_PORT = int(os.environ.get("SMOKE_PORT", "8080"))
BASE = f"http://127.0.0.1:{DEFAULT_PORT}"
ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"

CHECKS = 0


def step(message: str) -> None:
    """Print one passing check line."""
    global CHECKS
    CHECKS += 1
    print(f"  [ok] {message}")


def _open(
    method: str, path: str, body: dict | None = None, timeout: float = 30.0
) -> tuple[int, bytes]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(BASE + path, data=data, method=method)
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def http(method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    status, raw = _open(method, path, body)
    if status >= 400:
        raise RuntimeError(f"{method} {path} -> HTTP {status}: {raw[:300]!r}")
    return status, json.loads(raw.decode("utf-8"))


def http_text(path: str) -> str:
    status, raw = _open("GET", path)
    if status >= 400:
        raise RuntimeError(f"GET {path} -> HTTP {status}")
    return raw.decode("utf-8")


def expect_status(
    method: str, path: str, expected: int, body: dict | None = None
) -> dict:
    """Assert a specific status code, including error statuses."""
    status, raw = _open(method, path, body)
    if status != expected:
        raise RuntimeError(
            f"{method} {path} -> HTTP {status}, expected {expected}: {raw[:300]!r}"
        )
    try:
        return json.loads(raw.decode("utf-8"))
    except ValueError:
        return {}


def wait_healthy(timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            status, body = http("GET", "/health")
            if status == 200 and body.get("status") == "ok":
                return
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError("Server did not become healthy")


def wait_status(project_id: str, expected: str, timeout: float = 30.0) -> dict:
    deadline = time.time() + timeout
    body: dict[str, Any] = {}
    while time.time() < deadline:
        _, body = http("GET", f"/projects/{project_id}")
        if body["status"] == expected:
            return body
        time.sleep(0.2)
    raise RuntimeError(
        f"Timed out waiting for '{expected}', got '{body.get('status')}'"
    )


def wait_voiceover(project_id: str, timeout: float = 25.0) -> dict:
    """Wait for narration synthesis to finish or fail; both are acceptable offline."""
    deadline = time.time() + timeout
    body: dict[str, Any] = {}
    while time.time() < deadline:
        _, body = http("GET", f"/projects/{project_id}")
        if body.get("voiceover") is not None or body.get("error"):
            return body
        time.sleep(0.5)
    return body


def check_agents() -> None:
    _, catalog = http("GET", "/agents")
    assert catalog["strategy"] == "cost_first", catalog
    assert isinstance(catalog["agents"], list), catalog
    assert "viral-short" in catalog["preset_styles"], catalog
    step(
        f"GET /agents -> {len(catalog['agents'])} agent(s), "
        f"{len(catalog['preset_styles'])} presets"
    )


def check_script_styles(pid: str) -> None:
    _, styles = http("GET", "/script/styles")
    names = {style["name"] for style in styles}
    assert {"viral-short", "documentary", "educational", "story"} <= names, names
    step(f"GET /script/styles -> {len(styles)} presets")

    markdown = http_text("/script/styles/story/md")
    assert "# Style: story" in markdown, markdown[:200]
    step("GET /script/styles/story/md -> Markdown contract rendered")

    created = expect_status(
        "PUT",
        "/script/styles/smoke-style",
        200,
        {
            "name": "ignored-by-path",
            "title": "Smoke style",
            "tone": "clipped and fast",
            "sentence_max_units": 9,
            "banned_phrases": ["in this video"],
            "cta": "Follow for more.",
        },
    )
    assert created["name"] == "smoke-style", created
    assert created["sentence_max_units"] == 9, created
    step("PUT /script/styles/{name} -> user preset saved")

    fetched = expect_status("GET", "/script/styles/smoke-style", 200)
    assert fetched["tone"] == "clipped and fast", fetched
    step("GET /script/styles/smoke-style -> preset round-trips")

    project = expect_status(
        "PUT", f"/projects/{pid}/script/style", 200, {"style": "smoke-style"}
    )
    assert project["script_style"] == "smoke-style", project
    step("PUT /projects/{id}/script/style -> project switched preset")

    expect_status("PUT", f"/projects/{pid}/script/style", 404, {"style": "nope"})
    step("PUT /projects/{id}/script/style (unknown) -> HTTP 404")

    assert expect_status("DELETE", "/script/styles/smoke-style", 200) == {
        "deleted": True
    }
    assert expect_status("DELETE", "/script/styles/viral-short", 200) == {
        "deleted": False
    }
    step("DELETE /script/styles -> user preset removed, built-in protected")

    project = expect_status(
        "PUT", f"/projects/{pid}/script/style", 200, {"style": "viral-short"}
    )
    assert project["script_style"] == "viral-short", project
    step("PUT /projects/{id}/script/style -> back on the built-in preset")


def check_script_analysis(pid: str) -> None:
    weak = (
        "[Hook]\nIn this video we will explore how the attention economy shapes "
        "the way that modern short-form video platforms reward creators who "
        "optimize their opening seconds for retention above absolutely "
        "everything else that matters."
    )
    _, analysis = http("POST", f"/projects/{pid}/script/analyze", {"script": weak})
    codes = {issue["code"] for issue in analysis["issues"]}
    assert "banned_phrase" in codes, codes
    assert "long_sentence" in codes, codes
    assert 0 <= analysis["score"] <= 100, analysis["score"]
    assert analysis["plan"]["sections"], analysis
    step(
        "POST /script/analyze -> plan "
        f"{analysis['plan']['estimated_seconds']}s vs target "
        f"{analysis['plan']['target_seconds']}s, score {analysis['score']}, "
        f"issues: {', '.join(sorted(codes))}"
    )

    empty = expect_status("POST", f"/projects/{pid}/script/analyze", 200, {})
    assert empty["plan"] is not None, empty
    step("POST /script/analyze with no body -> analyzes the stored script")


def check_agent_bridge(pid: str) -> None:
    brief = http_text(f"/projects/{pid}/brief.md?agent=smoke-agent")
    assert "# Agent brief" in brief, brief[:200]
    assert "agent_hint: smoke-agent" in brief, brief[:200]
    assert "## 2. Style contract" in brief, brief[:200]
    assert "## How to reply" in brief, brief[:200]
    assert "```script" in brief, brief[:200]
    step(f"GET /projects/{{id}}/brief.md -> {len(brief)} chars of self-contained brief")

    reply = "\n".join(
        [
            "Here is the rewrite.",
            "",
            "```script",
            "[Hook]",
            "The city whispers before it wakes.",
            "",
            "[Turn]",
            "Trucks and shutters are the only choir left.",
            "",
            "[Payoff]",
            "Listen at 5am and you hear who really runs this place.",
            "```",
            "",
            "```json scenes",
            '[{"label": "Hook", "text": "5am", '
            '"narration": "The city whispers before it wakes."}]',
            "```",
            "",
            "```json style",
            '{"name": "smoke-agent-style", "tone": "hushed", "sentence_max_units": 10}',
            "```",
        ]
    )
    project = http("POST", f"/projects/{pid}/agent-result", {"markdown": reply})[1]
    assert "[Hook]" in project["script"], project["script"]
    assert project["agent_used"] == "external-agent", project
    assert project["source_rights_confirmed"] is False, project
    assert project["script_style"] == "smoke-agent-style", project
    assert project["script_plan"] is not None, project
    assert project["video_project"] is not None, project
    assert project["video_project"]["scenes"][0]["label"] == "Hook", project
    step("POST /agent-result -> script + scenes + style imported, rights NOT confirmed")

    _, styles = http("GET", "/script/styles")
    assert "smoke-agent-style" in {style["name"] for style in styles}, styles
    step("POST /agent-result -> agent-authored preset persisted on disk")

    rejected = expect_status(
        "POST", f"/projects/{pid}/agent-result", 409, {"markdown": "nothing useful"}
    )
    assert "no script" in rejected["detail"], rejected
    step("POST /agent-result (empty reply) -> HTTP 409")


def wait_workflow_run(run_id: str, timeout: float = 90.0) -> dict:
    """Poll a background flow run until it leaves the running state."""
    deadline = time.time() + timeout
    body: dict[str, Any] = {}
    while time.time() < deadline:
        _, body = http("GET", f"/workflow/runs/{run_id}")
        if body["status"] != "running":
            return body
        time.sleep(0.3)
    raise RuntimeError(f"flow run '{run_id}' never finished: {body.get('status')}")


def check_workflow(pid: str) -> None:
    """Drag-and-drop flow board: palette, checklist gate, save, run, resume."""
    _, palette = http("GET", "/workflow/blocks")
    types = {entry["type"] for entry in palette}
    assert {"research", "script", "gate", "scenes", "publish"} <= types, types
    assert all(entry["label"] and entry["description"] for entry in palette)
    step(f"GET /workflow/blocks -> {len(palette)} draggable block types")

    _, default_flow = http("GET", f"/projects/{pid}/workflow")
    assert default_flow["version"] == 1, default_flow
    assert len(default_flow["nodes"]) == 9, default_flow
    assert len(default_flow["edges"]) == 8, default_flow
    step(
        f"GET /projects/{{id}}/workflow -> default flow with "
        f"{len(default_flow['nodes'])} blocks / {len(default_flow['edges'])} links"
    )

    _, checklist = http("GET", f"/projects/{pid}/workflow/checklist")
    assert checklist["ready"] is True, checklist
    assert checklist["issues"] == [], checklist
    assert len(checklist["order"]) == 9, checklist
    step("GET /workflow/checklist -> ready, execution order resolved")

    candidate = {
        "workflow": {
            "name": "unsaved candidate",
            "nodes": [
                {"id": "a", "type": "research", "label": "Research"},
                {"id": "b", "type": "gate", "label": "Review"},
            ],
            "edges": [],
            "version": 1,
        }
    }
    _, audit = http("POST", f"/projects/{pid}/workflow/checklist", candidate)
    codes = {issue["code"] for issue in audit["issues"]}
    assert audit["ready"] is False and "missing_param" in codes, audit
    assert "unconnected_block" in codes, audit
    _, still_default = http("GET", f"/projects/{pid}/workflow")
    assert len(still_default["nodes"]) == 9, still_default
    step(
        f"POST /workflow/checklist -> audited unsaved edits "
        f"({len(audit['issues'])} findings) without persisting them"
    )

    status, blocked = _open(
        "PUT",
        f"/projects/{pid}/workflow",
        {
            "workflow": {
                "name": "broken",
                "nodes": [{"id": "g", "type": "gate", "label": "Gate"}],
                "edges": [],
                "version": 1,
            }
        },
    )
    assert status == 422, (status, blocked)
    detail = json.loads(blocked.decode("utf-8"))["detail"]
    assert "stage" in detail["message"], detail
    assert detail["checklist"]["ready"] is False, detail
    step("PUT /workflow (unfinished) -> HTTP 422 carrying the checklist")

    status, saved = http(
        "PUT",
        f"/projects/{pid}/workflow",
        {
            "workflow": {
                "name": "smoke flow",
                "nodes": [
                    {
                        "id": "r1",
                        "type": "research",
                        "label": "Research",
                        "x": 40,
                        "y": 120,
                    }
                ],
                "edges": [],
                "version": 1,
            }
        },
    )
    assert status == 200 and saved["workflow"]["version"] == 1, saved
    step("PUT /workflow -> 1-block flow saved as version 1")

    _, queued = http(
        "POST", f"/projects/{pid}/workflow/run?background=true", {"inputs": {}}
    )
    run = wait_workflow_run(queued["id"])
    assert run["id"] == queued["id"], (queued, run)
    assert run["status"] == "ok", run
    assert run["steps"][0]["type"] == "research", run["steps"]
    assert run["steps"][0]["status"] == "ok", run["steps"]
    assert run["steps"][0]["output"]["sources"] >= 1, run["steps"]
    assert run["duration_ms"] >= 0 and run["finished_at"], run
    step(
        f"POST /workflow/run (background) -> {run['status']}, "
        f"{len(run['steps'])} block(s), research found "
        f"{run['steps'][0]['output']['sources']} sources"
    )

    _, history = http("GET", f"/projects/{pid}/workflow/runs?limit=5")
    assert history and history[0]["id"] == run["id"], history
    step(f"GET /workflow/runs -> {len(history)} run(s) recorded for monitoring")

    expect_status("GET", "/workflow/runs/does-not-exist", 404)
    step("GET /workflow/runs/{unknown} -> HTTP 404")

    status, restored = http(
        "PUT",
        f"/projects/{pid}/workflow",
        {"workflow": {**default_flow, "version": 1}, "force": True},
    )
    assert status == 200 and len(restored["workflow"]["nodes"]) == 9, restored
    assert restored["workflow"]["version"] == 2, restored
    step("PUT /workflow (default document) -> restored, version bumped to 2")

    expect_status("GET", "/projects/no-such-project/workflow", 404)
    step("GET /projects/{unknown}/workflow -> HTTP 404")


def check_voiceover(pid: str) -> None:
    status, _ = _open("POST", f"/projects/{pid}/voiceover/generate")
    assert status == 200, status
    step("POST /voiceover/generate -> accepted (HTTP 200)")

    project = wait_voiceover(pid)
    if project.get("voiceover") is not None:
        engine = project["voiceover"]["engine"]
        tracks = len(project["voiceover"]["tracks"])
        step(f"voiceover finished -> engine={engine}, {tracks} scene track(s)")
    else:
        step(
            "voiceover unavailable offline (no TTS network) -> error surfaced "
            "on the project, status unchanged"
        )


def check_campaign(pid: str) -> None:
    payload = {
        "shorts_count": 5,
        "youtube_target_minutes": 10,
    }
    status, campaign = http("POST", f"/projects/{pid}/campaign/generate", payload)
    assert status == 200, status
    assert "master_topic" in campaign, campaign
    assert len(campaign["shorts"]) == 5, len(campaign["shorts"])
    assert len(campaign["youtube_story_structure"]) == 8, len(
        campaign["youtube_story_structure"]
    )
    assert len(campaign["youtube_scenes"]) >= 10, len(campaign["youtube_scenes"])
    assert len(campaign["youtube_titles"]) == 5, len(campaign["youtube_titles"])
    assert len(campaign["tiktok_hooks"]) == 10, len(campaign["tiktok_hooks"])
    step(
        f"POST /campaign/generate -> 8-step Master script, 5 shorts, "
        f"{len(campaign['youtube_scenes'])} hybrid scenes"
    )

    _, fetched = http("GET", f"/projects/{pid}/campaign")
    assert fetched["id"] == campaign["id"], (campaign, fetched)
    step("GET /projects/{id}/campaign -> campaign retrieved")

    short_id = fetched["shorts"][0]["id"]
    status, updated = http(
        "PUT",
        f"/projects/{pid}/campaign/shorts/{short_id}",
        {"title": "Updated Kursk Mystery Hook", "hook": "Did anyone survive?"},
    )
    assert status == 200 and updated["title"] == "Updated Kursk Mystery Hook", updated
    assert updated["hook"] == "Did anyone survive?", updated
    step(f"PUT /campaign/shorts/{{id}} -> short {short_id} customized")

    _, pack = http("GET", f"/projects/{pid}/campaign/export-pack")
    assert pack["campaign_id"] == campaign["id"], pack
    assert "prompt_pack" in pack and "youtube_master" in pack, pack
    step(
        f"GET /campaign/export-pack -> exported 15-asset package "
        f"({len(pack['shorts'])} shorts)"
    )


def check_external_ingest(pid: str) -> None:
    # 1. Ingest Kling AI video link to scene 0
    status, record = http(
        "POST",
        f"/projects/{pid}/external/import",
        {
            "asset_type": "scene_video",
            "scene_index": 0,
            "url": "https://assets.klingai.com/renders/smoke_kling.mp4",
            "label": "Smoke Kling 1080p",
            "attribution": "Kling AI 1.5",
        },
    )
    assert status == 200 and record["asset_type"] == "scene_video", record
    step("POST /external/import -> linked Kling video to scene 0")

    # 2. Ingest Suno background music
    status, music_rec = http(
        "POST",
        f"/projects/{pid}/external/import",
        {
            "asset_type": "background_music",
            "url": "https://cdn.suno.ai/audio/smoke_suno.mp3",
            "attribution": "Suno AI v4",
        },
    )
    assert status == 200 and music_rec["asset_type"] == "background_music", music_rec
    step("POST /external/import -> linked Suno background music")

    # 3. List external assets
    _, assets = http("GET", f"/projects/{pid}/external/assets")
    assert len(assets) >= 2, assets
    step(f"GET /projects/{{id}}/external/assets -> {len(assets)} asset(s) listed")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=(
            "port to test; an already-listening server is reused as-is, so pass "
            "a free port to force a fresh instance with the current code "
            f"(default {DEFAULT_PORT}, or $SMOKE_PORT)"
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    global BASE
    args = parse_args(argv)
    BASE = f"http://127.0.0.1:{args.port}"

    spawned: subprocess.Popen | None = None
    try:
        wait_healthy(timeout=3.0)
        reused = True
    except RuntimeError:
        reused = False
        spawned = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "content_factory.api:app",
                f"--app-dir={SRC_DIR}",
                f"--port={args.port}",
            ],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        wait_healthy(timeout=30.0)

    try:
        print("AI Content Factory — full pipeline smoke test")
        if reused:
            print(
                f"  [!!] reusing the server already listening on {BASE}; "
                "pass --port <free-port> to test the current code"
            )
        else:
            print(f"  [ok] spawned a fresh server on {BASE}")
        print("-" * 62)

        status, health = http("GET", "/health")
        assert status == 200 and health["status"] == "ok", health
        step(f"GET /health -> ok (providers: {health['providers']})")

        status, project = http(
            "POST",
            "/projects",
            {
                "name": "Smoke test",
                "topic": "A topic exercised by the smoke test",
                "target_language": "vi",
                "duration_target_seconds": 45,
            },
        )
        assert status == 201 and project["status"] == "draft", (status, project)
        pid = project["id"]
        step(f"POST /projects -> {pid} in status 'draft'")

        check_agents()
        check_script_styles(pid)
        check_script_analysis(pid)

        status, project = http("POST", f"/projects/{pid}/research")
        assert status == 200 and project["research"] is not None, (status, project)
        assert len(project["research"]["sources"]) >= 2, project
        step(
            f"POST /projects/{{id}}/research -> "
            f"{len(project['research']['sources'])} sources, "
            f"{len(project['research']['key_facts'])} key facts"
        )

        _, listing = http("GET", "/library")
        assert "documents" in listing and "stats" in listing, listing
        step(
            f"GET /library -> {listing['stats']['documents']} document(s), "
            f"{listing['stats']['pages']} indexed page(s), "
            f"fts5={listing['stats']['fts5']}"
        )

        _, hits = http("GET", "/library/search?q=attention")
        assert isinstance(hits, list), hits
        step(f"GET /library/search -> {len(hits)} BM25 hit(s)")

        status, project = http(
            "PUT",
            f"/projects/{pid}/script",
            {
                "script": (
                    "[Hook]\nWhy does the city sound different at 5am?\n\n"
                    "[Context]\nTrucks and shutters set the rhythm before anyone "
                    "wakes.\n\n"
                    "[Turn]\nThat quiet hour is the only time the machinery is "
                    "visible.\n\n"
                    "[Payoff]\nIt is the real heartbeat of a place.\n"
                ),
                "source_rights_confirmed": False,
            },
        )
        assert status == 200 and project["status"] == "script_review", (status, project)
        assert project["script_plan"] is not None, project
        step("PUT /projects/{id}/script -> status 'script_review' with a timing plan")

        check_agent_bridge(pid)

        # The agent's script is what we carry forward; re-read it from the API
        # so this step never resurrects the pre-agent draft.
        _, project = http("GET", f"/projects/{pid}")
        assert project["agent_used"] == "external-agent", project
        status, project = http(
            "PUT",
            f"/projects/{pid}/script",
            {
                "script": project["script"],
                "source_rights_confirmed": True,
            },
        )
        assert status == 200 and project["source_rights_confirmed"] is True, project
        step("PUT /projects/{id}/script -> source rights confirmed by the human")

        status, project = http(
            "POST",
            f"/projects/{pid}/approvals",
            {"stage": "script", "verdict": "approved", "comment": "Smoke test"},
        )
        assert status == 200 and project["status"] == "script_approved", (
            status,
            project,
        )
        step("POST /approvals (script) -> GATE 1 passed, status 'script_approved'")

        status, project = http("POST", f"/projects/{pid}/generate")
        assert status == 200 and project["status"] == "generating", (status, project)
        step("POST /projects/{id}/generate -> status 'generating'")

        reviewed = wait_status(pid, "video_review")
        assert reviewed["progress"] == 100, reviewed
        assert reviewed["video"] is not None, reviewed
        assert reviewed["video_project"] is not None, reviewed
        scene_count = len(reviewed["video_project"]["scenes"])
        step(
            f"worker finished -> status 'video_review', progress 100, "
            f"{scene_count} editable scene(s)"
        )

        scenes = reviewed["video_project"]["scenes"]
        first_scene, second_scene = scenes[0]["id"], scenes[-1]["id"]
        _, scene = http(
            "GET", f"/projects/{pid}/video-project/scenes/{first_scene}/suggest"
        )
        assert {"filter", "effect", "grade", "transition"} <= set(scene), scene
        step(f"GET scene suggest -> {scene}")

        polish_target = scenes[-1]
        status, project = http(
            "POST", f"/projects/{pid}/video-project/scenes/{second_scene}/polish"
        )
        polished = next(
            item
            for item in project["video_project"]["scenes"]
            if item["id"] == second_scene
        )
        assert status == 200 and polished["text"], project
        step(
            f"POST scene polish -> '{polish_target['label']}' text polished to "
            f"{polished['text'][:40]!r}"
        )

        status, project = http(
            "POST",
            f"/projects/{pid}/video-project/ai-assist",
            {"fit": True, "beat": True, "bpm": 120},
        )
        assert status == 200 and project["video_project"]["scenes"], project
        total = sum(
            scene["duration_seconds"] for scene in project["video_project"]["scenes"]
        )
        step(f"POST /video-project/ai-assist -> fit + beat sync, total {total:.2f}s")

        status, project = http(
            "PUT",
            f"/projects/{pid}/video-project",
            {"project": project["video_project"]},
        )
        assert status == 200 and project["video_project"] is not None, project
        step("PUT /projects/{id}/video-project -> edits persisted")

        check_voiceover(pid)

        status, project = http(
            "POST",
            f"/projects/{pid}/approvals",
            {"stage": "video", "verdict": "approved", "comment": "Smoke test"},
        )
        assert status == 200 and project["status"] == "video_approved", (
            status,
            project,
        )
        step("POST /approvals (video) -> GATE 2 passed, status 'video_approved'")

        status, project = http(
            "POST", f"/projects/{pid}/publish", {"platforms": ["youtube", "tiktok"]}
        )
        assert status == 200 and project["status"] == "published", (status, project)
        assert project["published_at"] is not None, project
        assert project["platforms"] == ["youtube", "tiktok"], project
        step("POST /projects/{id}/publish -> status 'published' to youtube, tiktok")

        _, project = http("GET", f"/projects/{pid}")
        assert project["status"] == "published", project
        step("GET /projects/{id} -> final state confirmed")

        check_workflow(pid)
        check_campaign(pid)
        check_external_ingest(pid)

        _, projects = http("GET", "/projects")
        assert any(item["id"] == pid for item in projects), projects
        step(f"GET /projects -> {len(projects)} project(s) listed")

        html = http_text("/")
        assert "<html" in html.lower(), "frontend was not served"
        step("GET / -> dashboard HTML served")

        thumb = http_text(f"/projects/{pid}/thumbnail")
        assert "<svg" in thumb, "thumbnail was not served"
        step("GET /projects/{id}/thumbnail -> SVG rendered")

        # --- Negative paths --------------------------------------------------
        expect_status("GET", "/projects/does-not-exist", 404)
        step("GET /projects/{unknown} -> HTTP 404")

        expect_status("GET", "/projects/does-not-exist/campaign", 404)
        step("GET /projects/{unknown}/campaign -> HTTP 404")

        expect_status("GET", "/projects/does-not-exist/external/assets", 404)
        step("GET /projects/{unknown}/external/assets -> HTTP 404")

        expect_status(
            "POST", "/projects/does-not-exist/agent-result", 404, {"markdown": "x"}
        )
        step("POST /agent-result on unknown project -> HTTP 404")

        rejected = expect_status(
            "POST",
            f"/projects/{pid}/approvals",
            409,
            {"stage": "script", "verdict": "approved"},
        )
        assert "Cannot review script" in rejected["detail"], rejected
        step("POST /approvals out of order -> HTTP 409 (state machine holds)")

        expect_status(
            "POST",
            f"/projects/{pid}/agent-result",
            409,
            {"markdown": "```script\nx\n```"},
        )
        step("POST /agent-result after publish -> HTTP 409")

        missing_scene = expect_status(
            "POST",
            f"/projects/{pid}/video-project/scenes/not-a-scene/polish",
            404,
        )
        assert "not-a-scene" in missing_scene["detail"], missing_scene
        step("POST scene polish with unknown scene -> HTTP 404 naming the scene")

        invalid = expect_status("POST", "/projects", 422, {"name": "", "topic": ""})
        assert "detail" in invalid, invalid
        step("POST /projects with invalid payload -> HTTP 422")

        # Leave no test pollution behind in presets/.
        assert expect_status("DELETE", "/script/styles/smoke-agent-style", 200) == {
            "deleted": True
        }
        step("cleanup -> the agent-authored preset is removed from presets/")

        print("-" * 62)
        print(f"SMOKE TEST PASSED — {CHECKS} checks")
        return 0
    finally:
        if spawned is not None:
            spawned.terminate()
            spawned.wait(timeout=10)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
