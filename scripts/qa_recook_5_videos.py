"""Re-cook QA: build 5 source videos, transcribe them, and re-cook each.

Demonstrates the full "xào nấu" (content re-cook) pipeline end-to-end over real
HTTP:

  1. Synthesize a ~60s narration for each of 5 war topics (edge-tts).
  2. Wrap each narration into a real source video (colour card + audio).
  3. Upload each source to the universal media library.
  4. Transcribe it with faster-whisper so an AI agent can read it.
  5. Re-cook it into a brand-new project (re-worded script, new title).
  6. Drive the two mandatory human gates + production + ffmpeg render.
  7. Verify the new video is a probeable WebM.

If nothing is listening it spawns its own uvicorn instance. Exits 0 only when
every re-cooked project published a probeable WebM.
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

DEFAULT_PORT = int(os.environ.get("RECOOK_PORT", "8080"))
ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"

TOPICS = [
    ("WWI Verdun", "World War I: the Battle of Verdun"),
    ("WWII Stalingrad", "World War II: the Battle of Stalingrad"),
    ("Vietnam Trail", "Vietnam War: the Ho Chi Minh Trail"),
    ("Waterloo", "Napoleonic Wars: the Battle of Waterloo"),
    ("Punic Wars", "Punic Wars: Rome and Carthage"),
]

NARRATION = {
    "WWI Verdun": (
        "The Battle of Verdun began in February 1916 and lasted for ten months. "
        "It was one of the longest and most brutal battles of the First World War. "
        "German forces attacked French positions along the Meuse River. "
        "The French held the line with extraordinary endurance. "
        "Nearly seven hundred thousand soldiers became casualties. "
        "Verdun became a symbol of French national determination. "
        "The fortress city never fell to the enemy. "
        "Its defenders turned a desperate defense into a lasting legend."
    ),
    "WWII Stalingrad": (
        "The Battle of Stalingrad lasted from August 1942 to February 1943. "
        "It was one of the bloodiest battles in all of history. "
        "Soviet forces defended the city street by street. "
        "German troops pushed deep into the urban ruins. "
        "Winter arrived and trapped the attackers in the rubble. "
        "Soviet armies surrounded the entire German Sixth Army. "
        "The surrender marked a decisive turning point in the war. "
        "Stalingrad changed the course of the Eastern Front forever."
    ),
    "Vietnam Trail": (
        "The Ho Chi Minh Trail was a vast network of jungle roads. "
        "It connected North Vietnam to the battlefields of the South. "
        "Supplies and troops moved along hidden mountain paths. "
        "American bombing tried to cut the route for years. "
        "Engineers constantly rebuilt the damaged sections overnight. "
        "The trail stretched across Laos and Cambodia as well. "
        "It proved that logistics could overcome air power. "
        "The network became the lifeline of the entire war effort."
    ),
    "Waterloo": (
        "The Battle of Waterloo took place on June eighteenth, eighteen fifteen. "
        "Napoleon faced a coalition of British and Prussian forces. "
        "The fighting raged across muddy fields near Brussels. "
        "Wellington held his line against repeated French attacks. "
        "The Prussians arrived late in the afternoon to decide the day. "
        "Napoleon's army collapsed and fled the battlefield. "
        "The defeat ended his reign and the Napoleonic era. "
        "Waterloo reshaped the political map of all of Europe."
    ),
    "Punic Wars": (
        "The Punic Wars were fought between Rome and Carthage. "
        "They spanned more than a century of bitter conflict. "
        "Hannibal crossed the Alps with war elephants to invade Italy. "
        "Rome answered by building a powerful navy at sea. "
        "The wars destroyed Carthage as a Mediterranean power. "
        "Rome rose to dominate the entire Mediterranean world. "
        "The struggle decided the fate of western civilization. "
        "Its lessons echoed through military history for ages."
    ),
}


class Client:
    def __init__(self, base: str) -> None:
        self.base = base

    def _open(self, method, path, body=None, timeout=120.0, raw=False):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read()

    def http(self, method, path, body=None, timeout=120.0):
        status, raw = self._open(method, path, body, timeout)
        if status >= 400:
            raise RuntimeError(f"{method} {path} -> HTTP {status}: {raw[:300]!r}")
        return status, json.loads(raw.decode("utf-8"))

    def upload(self, path: Path, language: str = "en"):
        """Multipart upload a file to /media/upload."""
        boundary = "----recook" + os.urandom(8).hex()
        filename = path.name
        content = path.read_bytes()
        body = b""
        body += f"--{boundary}\r\n".encode()
        disp = f'Content-Disposition: form-data; name="language"\r\n\r\n{language}\r\n'
        body += disp.encode()
        body += f"--{boundary}\r\n".encode()
        body += (
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            "Content-Type: application/octet-stream\r\n\r\n"
        ).encode()
        body += content + b"\r\n"
        body += f"--{boundary}--\r\n".encode()
        req = urllib.request.Request(
            self.base + "/media/upload", data=body, method="POST"
        )
        req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
        with urllib.request.urlopen(req, timeout=180) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def wait_status(self, pid, expected, timeout=120.0):
        deadline = time.time() + timeout
        body = {}
        while time.time() < deadline:
            _, body = self.http("GET", f"/projects/{pid}")
            if body["status"] == expected:
                return body
            time.sleep(0.3)
        status = body.get("status")
        raise RuntimeError(f"timeout waiting for '{expected}', got '{status}'")

    def wait_voiceover(self, pid, timeout=180.0):
        """Poll until the project has a synthesized voiceover bundle."""
        deadline = time.time() + timeout
        body = {}
        while time.time() < deadline:
            _, body = self.http("GET", f"/projects/{pid}")
            vo = body.get("voiceover")
            if vo and vo.get("tracks"):
                return body
            time.sleep(0.5)
        raise RuntimeError("timeout waiting for voiceover synthesis")


def synthesize_narration(text: str, out: Path) -> bool:
    """Synthesize narration with edge-tts; return True on success."""
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "edge_tts",
        "--voice",
        "en-US-JennyNeural",
        "--text",
        text,
        "--write-media",
        str(out),
    ]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0 and out.is_file() and out.stat().st_size > 0


def make_source_video(narration_mp3: Path, out: Path) -> None:
    """Wrap a narration into a colour-card video with the audio track."""
    out.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=0x2b3a55:s=1080x1920:r=30:d=60",
            "-i",
            str(narration_mp3),
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-crf",
            "28",
            "-c:a",
            "aac",
            "-shortest",
            "-pix_fmt",
            "yuv420p",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"source video failed: {proc.stderr.strip()[-300:]}")


def drive_project(client: Client, pid: str, outdir: Path) -> dict:
    """Drive a re-cooked project through gates + production + render."""
    # Confirm source rights (mandatory human gate) then approve script.
    _, project = client.http("GET", f"/projects/{pid}")
    _, project = client.http(
        "PUT",
        f"/projects/{pid}/script",
        {"script": project["script"], "source_rights_confirmed": True},
    )
    _, project = client.http(
        "POST",
        f"/projects/{pid}/approvals",
        {"stage": "script", "verdict": "approved", "comment": "Re-cook QA"},
    )
    assert project["status"] == "script_approved", project
    _, project = client.http("POST", f"/projects/{pid}/generate")
    project = client.wait_status(pid, "video_review")
    # Self-edit then render.
    _, project = client.http(
        "POST",
        f"/projects/{pid}/video-project/ai-assist",
        {"fit": True, "beat": True, "bpm": 120},
    )
    # Generate the voiceover so the final video has narration + music.
    client.http("POST", f"/projects/{pid}/voiceover/generate")
    project = client.wait_voiceover(pid)
    outdir.mkdir(parents=True, exist_ok=True)
    webm = outdir / f"{pid}.webm"
    _, project = client.http("POST", f"/projects/{pid}/render", timeout=480)
    assert project["video"] is not None, project
    urllib.request.urlretrieve(client.base + project["video"]["asset_url"], webm)
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=codec_name,codec_type",
            "-of",
            "json",
            str(webm),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    info = json.loads(probe.stdout) if probe.returncode == 0 else {"streams": []}
    streams = info.get("streams") or []
    assert streams, f"no streams in {webm}"
    assert any(s.get("codec_type") == "video" for s in streams), "no video stream"
    assert any(s.get("codec_type") == "audio" for s in streams), "no audio stream"
    duration = float(info.get("format", {}).get("duration", 0) or 0)
    # Approve final video + publish.
    _, project = client.http(
        "POST",
        f"/projects/{pid}/approvals",
        {"stage": "video", "verdict": "approved", "comment": "Re-cook QA"},
    )
    _, project = client.http(
        "POST", f"/projects/{pid}/publish", {"platforms": ["youtube", "tiktok"]}
    )
    assert project["status"] == "published", project
    return {
        "duration": round(duration, 2),
        "size": webm.stat().st_size,
        "webm": str(webm),
        "audio_streams": sum(1 for s in streams if s.get("codec_type") == "audio"),
    }


def wait_healthy(base, timeout=30.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            req = urllib.request.Request(base + "/health")
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200 and json.loads(resp.read()).get("status") == "ok":
                    return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def main(argv=None):
    default_out = str(ROOT / "scratch" / "recook_videos")
    default_src = str(ROOT / "scratch" / "recook_sources")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--outdir", type=str, default=default_out)
    parser.add_argument("--src-out", type=str, default=default_src)
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

    client = Client(base)
    src_out = Path(args.src_out)
    outdir = Path(args.outdir)
    results = []
    try:
        for index, (name, topic) in enumerate(TOPICS, start=1):
            row = {
                "index": index,
                "name": name,
                "topic": topic,
                "status": "failed",
                "error": "",
            }
            try:
                narration = src_out / f"{index}_narration.mp3"
                source_video = src_out / f"{index}_source.mp4"
                if not synthesize_narration(NARRATION[name], narration):
                    raise RuntimeError("edge-tts narration synthesis failed")
                make_source_video(narration, source_video)

                # Upload to media library.
                media = client.upload(source_video)
                media_id = media["id"]
                row["media_id"] = media_id
                row["kind"] = media["kind"]

                # Transcribe.
                media = client.http("POST", f"/media/{media_id}/transcribe")[1]
                transcript = media.get("transcription") or ""
                row["transcript_words"] = len(transcript.split())

                # Re-cook into a new project.
                recook = client.http(
                    "POST",
                    f"/media/{media_id}/recook",
                    {
                        "new_title": f"{name}: Re-cooked",
                        "language": "en",
                        "target_seconds": 60,
                        "mode": "balanced",
                        "change_music": True,
                    },
                )[1]
                pid = recook["project_id"]
                row["project_id"] = pid
                row["script_words"] = len(recook["script"].split())

                # Drive gates + production + render.
                out = drive_project(client, pid, outdir)
                row.update(out)
                row["status"] = "published"
                t_words = row["transcript_words"]
                s_words = row["script_words"]
                dur = row["duration"]
                sz = row["size"]
                print(
                    f"[PASS] #{index} {name:<18} transcript={t_words}w "
                    f"script={s_words}w dur={dur}s webm={sz}B"
                )
            except Exception as exc:  # noqa: BLE001
                row["error"] = str(exc)[:300]
                print(f"[FAIL] #{index} {name:<18} {row['error']}")
            results.append(row)

        passed = sum(1 for r in results if r["status"] == "published")
        failed = len(results) - passed
        print(f"\nSUMMARY total={len(results)} passed={passed} failed={failed}")
        for r in results:
            print(json.dumps(r, ensure_ascii=False))
        return 0 if passed == len(results) else 1
    finally:
        if spawned is not None:
            spawned.terminate()
            spawned.wait(timeout=10)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
