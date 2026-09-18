"""Live end-to-end test of the /tools agent API against a running server.

Run: python scripts/live_tools_test.py [base_url]
Every step goes through POST /tools/call only, exactly like an external AI
agent would drive the factory.
"""

from __future__ import annotations

import json
import sys
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8110"
failures: list[str] = []


def call(tool: str, args: dict | None = None):
    """POST /tools/call and return (status, body)."""
    payload = json.dumps({"tool": tool, "args": args or {}}).encode()
    req = urllib.request.Request(
        f"{BASE}/tools/call",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode())


def check(label: str, condition: bool) -> None:
    print(("PASS " if condition else "FAIL ") + label)
    if not condition:
        failures.append(label)


def main() -> int:
    # 0. Manifest
    with urllib.request.urlopen(f"{BASE}/tools", timeout=10) as resp:
        manifest = json.loads(resp.read().decode())
    check("manifest protocol", manifest.get("protocol") == "content-factory-tools/1")
    check("manifest has 30+ tools", manifest.get("count", 0) >= 30)

    # 1-4. Create, script, approve, build
    status, project = call(
        "create_project",
        {
            "name": "Live tools test",
            "topic": "Sóng thần Ấn Độ Dương 2004",
            "target_language": "vi",
            "duration_target_seconds": 45,
        },
    )
    check("create_project", status == 200 and "id" in project)
    pid = project["id"]

    status, project = call(
        "update_script",
        {
            "project_id": pid,
            "script": (
                "[Hook]\nTấn công không một tiếng động nào.\n\n"
                "[Turn]\nĐại dương rút lui để lấy đà.\n\n"
                "[Outro]\nBa đại dương gợn sóng trong một ngày."
            ),
            "source_rights_confirmed": True,
        },
    )
    check("update_script", status == 200)

    status, _ = call(
        "approve_stage",
        {
            "project_id": pid,
            "stage": "script",
            "verdict": "approved",
        },
    )
    check("approve_stage(script)", status == 200)

    status, project = call("build_video_project", {"project_id": pid})
    check("build_video_project", status == 200 and project["video_project"]["scenes"])
    sid = project["video_project"]["scenes"][0]["id"]

    status, _ = call("start_generation", {"project_id": pid})
    check("start_generation", status == 200)

    # 5-12. NLE-grade edits
    status, project = call(
        "set_scene_speed",
        {
            "project_id": pid,
            "scene_id": sid,
            "speed": 0.5,
        },
    )
    scene = project["video_project"]["scenes"][0]
    check("set_scene_speed 0.5x", status == 200 and scene["speed"] == 0.5)

    status, project = call(
        "reverse_scene",
        {
            "project_id": pid,
            "scene_id": sid,
            "reverse": True,
        },
    )
    check(
        "reverse_scene",
        status == 200 and project["video_project"]["scenes"][0]["reverse"] is True,
    )

    status, project = call(
        "trim_scene",
        {
            "project_id": pid,
            "scene_id": sid,
            "trim_start": 0.5,
            "trim_end": 2.0,
        },
    )
    scene = project["video_project"]["scenes"][0]
    check("trim_scene", status == 200 and scene["trim_start"] == 0.5)

    status, project = call(
        "set_scene_audio",
        {
            "project_id": pid,
            "scene_id": sid,
            "volume": 1.5,
            "fade_in": 0.3,
            "fade_out": 0.8,
        },
    )
    scene = project["video_project"]["scenes"][0]
    check(
        "set_scene_audio",
        status == 200
        and scene["volume"] == 1.5
        and scene["audio_fade_in"] == 0.3
        and scene["audio_fade_out"] == 0.8,
    )

    status, project = call(
        "split_scene",
        {
            "project_id": pid,
            "scene_id": sid,
            "at": 0.5,
        },
    )
    check("split_scene", status == 200 and len(project["video_project"]["scenes"]) == 4)

    status, project = call("duplicate_scene", {"project_id": pid, "scene_id": sid})
    check(
        "duplicate_scene",
        status == 200 and len(project["video_project"]["scenes"]) == 5,
    )

    status, project = call(
        "bulk_update_scenes",
        {
            "project_id": pid,
            "scene_ids": [sid],
            "patch": {"grade": "noir"},
        },
    )
    check(
        "bulk_update_scenes grade=noir",
        status == 200 and project["video_project"]["scenes"][0]["grade"] == "noir",
    )

    status, project = call(
        "add_marker",
        {
            "project_id": pid,
            "time_seconds": 5.0,
            "label": "beat 1",
        },
    )
    check("add_marker", status == 200 and len(project["video_project"]["markers"]) == 1)

    # 13-14. Verify
    status, report = call("timeline_report", {"project_id": pid})
    check("timeline_report", status == 200 and "score" in report)
    print(f"      score={report.get('score')} issues={len(report.get('issues', []))}")

    status, plan = call("render_plan", {"project_id": pid})
    check(
        "render_plan",
        status == 200 and plan["width"] == 1080 and plan["steps"] and plan["subtitles"],
    )
    print(
        f"      plan {plan['width']}x{plan['height']}@{plan['fps']}"
        f" steps={len(plan['steps'])} cues={len(plan['subtitles'])}"
    )

    # 15. Error mapping
    status, _ = call("no_such_tool", {})
    check("unknown tool -> 422", status == 422)
    status, body = call(
        "trim_scene",
        {
            "project_id": pid,
            "scene_id": "deadbeef",
            "trim_start": 1.0,
        },
    )
    check(
        "stale scene -> 404 + human message",
        status == 404 and "No scene" in body.get("detail", ""),
    )

    print()
    if failures:
        print(f"{len(failures)} FAILED: {failures}")
        return 1
    print("ALL LIVE TOOL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
