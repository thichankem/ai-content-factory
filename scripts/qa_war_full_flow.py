"""Full-flow QA driver: script creation -> self-edit -> real video render.

Drives several distinct war-history projects end-to-end over real HTTP and
produces a *real* ffmpeg WebM for each one (not just timeline metadata):

    draft -> script_review -> script_approved -> generating ->
    video_review -> (self-edit) -> render -> video_approved -> published

For every project it:
  * creates the project,
  * generates a script with the built-in offline template provider,
  * confirms source rights (mandatory human gate),
  * approves the script (GATE 1),
  * kicks off production and waits for the editable timeline,
  * self-edits: AI-assist fit+beat sync, a scene polish, timeline normalize,
  * renders the timeline to a real WebM with ffmpeg and probes it with ffprobe,
  * approves the final video (GATE 2),
  * publishes.

If nothing is listening it spawns its own uvicorn instance and shuts it down
afterwards. Prints one line per project and a summary table. Exits 0 only when
every project reached *published* and produced a probeable WebM.
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

DEFAULT_PORT = int(os.environ.get("QA_PORT", "8080"))
ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"

TOPICS = [
    ("WWI Verdun", "World War I: the Battle of Verdun"),
    ("WWII Stalingrad", "World War II: the Battle of Stalingrad"),
    ("Vietnam Trail", "Vietnam War: the Ho Chi Minh Trail"),
    ("Korean Pusan", "Korean War: the Pusan Perimeter"),
    ("Waterloo", "Napoleonic Wars: the Battle of Waterloo"),
    ("Civil War Vicksburg", "American Civil War: the Siege of Vicksburg"),
]


class Client:
    def __init__(self, base: str) -> None:
        self.base = base

    def _open(self, method: str, path: str, body: dict | None, timeout: float):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read()

    def http(
        self, method: str, path: str, body: dict | None = None, timeout: float = 60.0
    ):
        status, raw = self._open(method, path, body, timeout)
        if status >= 400:
            raise RuntimeError(f"{method} {path} -> HTTP {status}: {raw[:300]!r}")
        return status, json.loads(raw.decode("utf-8"))

    def expect(
        self,
        method: str,
        path: str,
        expected: int,
        body: dict | None = None,
        timeout: float = 60.0,
    ):
        status, raw = self._open(method, path, body, timeout)
        if status != expected:
            raise RuntimeError(
                f"{method} {path} -> HTTP {status}, expected {expected}: {raw[:300]!r}"
            )
        try:
            return json.loads(raw.decode("utf-8"))
        except ValueError:
            return {}

    def wait_status(self, pid: str, expected: str, timeout: float = 90.0) -> dict:
        deadline = time.time() + timeout
        body: dict[str, Any] = {}
        while time.time() < deadline:
            _, body = self.http("GET", f"/projects/{pid}")
            if body["status"] == expected:
                return body
            time.sleep(0.3)
        raise RuntimeError(
            f"timeout waiting for '{expected}', got '{body.get('status')}'"
        )


def probe_webm(path: Path) -> dict:
    """Return codec/duration/size from a WebM using ffprobe."""
    proc = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration,size:stream=codec_name,width,height",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {proc.stderr.strip()[:300]}")
    return json.loads(proc.stdout)


def run_project(
    client: Client, index: int, name: str, topic: str, outdir: Path
) -> dict:
    pid = ""
    try:
        _, project = client.http(
            "POST",
            "/projects",
            {
                "name": name,
                "topic": topic,
                "target_language": "en",
                "duration_target_seconds": 45,
            },
        )
        pid = project["id"]
        assert project["status"] == "draft", project

        # 1. Script creation via the offline template provider.
        _, project = client.http("POST", f"/projects/{pid}/script/generate")
        assert project["status"] == "script_review", project
        assert project.get("script"), "no script drafted"
        assert project.get("provider_used") == "template", project.get("provider_used")
        script_len = len(project["script"])

        # 2. Mandatory human confirmation of source rights.
        _, project = client.http(
            "PUT",
            f"/projects/{pid}/script",
            {"script": project["script"], "source_rights_confirmed": True},
        )
        assert project["source_rights_confirmed"] is True, project

        # 3. GATE 1: human script approval.
        _, project = client.http(
            "POST",
            f"/projects/{pid}/approvals",
            {"stage": "script", "verdict": "approved", "comment": "QA script approval"},
        )
        assert project["status"] == "script_approved", project

        # 4. Production -> editable timeline.
        _, project = client.http("POST", f"/projects/{pid}/generate")
        assert project["status"] == "generating", project
        project = client.wait_status(pid, "video_review")
        scenes = project["video_project"]["scenes"]
        assert scenes, "no scenes produced"

        # 5. Self-edit: AI-assist (fit + beat sync), a scene polish, normalize.
        _, project = client.http(
            "POST",
            f"/projects/{pid}/video-project/ai-assist",
            {"fit": True, "beat": True, "bpm": 120},
        )
        target_scene = project["video_project"]["scenes"][-1]["id"]
        _, project = client.http(
            "POST", f"/projects/{pid}/video-project/scenes/{target_scene}/polish"
        )
        _, project = client.http("POST", f"/projects/{pid}/timeline/normalize")

        # 6. Render a REAL WebM and verify it with ffprobe.
        outdir.mkdir(parents=True, exist_ok=True)
        webm = outdir / f"{pid}.webm"
        _, project = client.http("POST", f"/projects/{pid}/render", timeout=180)
        assert project["video"] is not None, project
        assert project["video"]["format"] == "webm", project
        # Download the served file and probe it.
        urllib.request.urlretrieve(client.base + project["video"]["asset_url"], webm)
        probe = probe_webm(webm)
        stream = probe["streams"][0]
        assert stream["codec_name"] == "vp9", stream
        assert float(probe["format"]["duration"]) >= 1.0, probe
        duration = float(probe["format"]["duration"])
        size = int(probe["format"]["size"])

        # 7. GATE 2: human final-video approval.
        _, project = client.http(
            "POST",
            f"/projects/{pid}/approvals",
            {"stage": "video", "verdict": "approved", "comment": "QA video approval"},
        )
        assert project["status"] == "video_approved", project

        # 8. Publish.
        _, project = client.http(
            "POST", f"/projects/{pid}/publish", {"platforms": ["youtube", "tiktok"]}
        )
        assert project["status"] == "published", project

        return {
            "index": index,
            "name": name,
            "id": pid,
            "topic": topic,
            "status": "published",
            "script_len": script_len,
            "scenes": len(scenes),
            "duration": round(duration, 2),
            "size_bytes": size,
            "webm": str(webm),
            "error": "",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "index": index,
            "name": name,
            "id": pid,
            "topic": topic,
            "status": "failed",
            "script_len": 0,
            "scenes": 0,
            "duration": 0,
            "size_bytes": 0,
            "webm": "",
            "error": str(exc)[:400],
        }


def wait_healthy(base: str, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            req = urllib.request.Request(base + "/health", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200 and json.loads(resp.read()).get("status") == "ok":
                    return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument(
        "--outdir", type=str, default=str(ROOT / "scratch" / "qa_videos")
    )
    args = parser.parse_args(argv)

    base = f"http://127.0.0.1:{args.port}"
    spawned = None
    if not wait_healthy(base, timeout=3.0):
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
        if not wait_healthy(base, timeout=30.0):
            print("Server did not become healthy.")
            return 1

    outdir = Path(args.outdir)
    client = Client(base)
    results = []
    try:
        for index, (name, topic) in enumerate(TOPICS, start=1):
            row = run_project(client, index, name, topic, outdir)
            results.append(row)
            status = "PASS" if row["status"] == "published" else "FAIL"
            print(
                f"[{status}] #{row['index']} {row['name']:<20} "
                f"scenes={row['scenes']} dur={row['duration']}s "
                f"webm={row['size_bytes']}B"
                + (f" | {row['error']}" if row["error"] else "")
            )

        passed = sum(1 for r in results if r["status"] == "published")
        print(
            f"\nSUMMARY total={len(results)} passed={passed} "
            f"failed={len(results) - passed}"
        )
        for r in results:
            print(json.dumps(r, ensure_ascii=False))
        return 0 if passed == len(results) else 1
    finally:
        if spawned is not None:
            spawned.terminate()
            spawned.wait(timeout=10)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
