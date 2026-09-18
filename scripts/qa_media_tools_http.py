"""Live check: drive the new media tools over real HTTP like an agent would."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

BASE = f"http://127.0.0.1:{sys.argv[1] if len(sys.argv) > 1 else 8131}"
WORK = Path(tempfile.mkdtemp(prefix="live-media-"))
CHECKS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    CHECKS.append((name, ok, detail))
    print(f"  [{'ok' if ok else 'FAIL'}] {name}{f' — {detail}' if detail else ''}")


def post_multipart(path: str, field: str, filename: str, blob: bytes) -> dict:
    boundary = uuid.uuid4().hex
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'
        "Content-Type: application/octet-stream\r\n\r\n"
    ).encode() + blob + f"\r\n--{boundary}--\r\n".encode()
    request = urllib.request.Request(
        f"{BASE}{path}",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read())


def get_json(path: str) -> dict:
    with urllib.request.urlopen(f"{BASE}{path}", timeout=30) as response:
        return json.loads(response.read())


def call(tool: str, args: dict) -> tuple[int, dict]:
    request = urllib.request.Request(
        f"{BASE}/tools/call",
        data=json.dumps({"tool": tool, "args": args}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read() or b"{}")


def wait_healthy(timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            get_json("/health")
            return
        except Exception:  # noqa: BLE001 - keep polling
            time.sleep(0.4)
    raise SystemExit("server did not become healthy")


print("waiting for the server ...")
wait_healthy()

print("generating fixtures ...")
video = WORK / "clip.mp4"
subprocess.run(
    [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=15:duration=3",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
        "-shortest", "-c:v", "libx264", "-preset", "ultrafast",
        "-pix_fmt", "yuv420p", "-c:a", "aac", str(video),
    ],
    check=True, capture_output=True,
)
music = WORK / "music.wav"
subprocess.run(
    [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "sine=frequency=330:duration=6",
        "-c:a", "pcm_s16le", str(music),
    ],
    check=True, capture_output=True,
)
photo = WORK / "logo.png"
subprocess.run(
    [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "color=c=orange:size=120x120:duration=1",
        "-frames:v", "1", str(photo),
    ],
    check=True, capture_output=True,
)

manifest = get_json("/tools")
check("GET /tools advertises schemas", manifest["count"] >= 55 and manifest["categories"], f"{manifest['count']} tools, schema={manifest.get('schema')}")
media_entries = [t for t in manifest["tools"] if t["category"] in {"media", "audio"}]
check("new media/audio tools listed", len(media_entries) >= 18, f"{len(media_entries)} tools")

video_item = post_multipart("/media/upload", "file", "clip.mp4", video.read_bytes())
music_item = post_multipart("/media/upload", "file", "music.wav", music.read_bytes())
photo_item = post_multipart("/media/upload", "file", "logo.png", photo.read_bytes())
check("upload video/music/photo", all([video_item.get("id"), music_item.get("id"), photo_item.get("id")]), f"{video_item['kind']}/{music_item['kind']}/{photo_item['kind']}")

status, reading = call("describe_media", {"ref": video_item["id"]})
sections = sorted(k for k in ("probe", "loudness", "silence", "scene_cuts", "palette", "music") if k in reading)
check("describe_media reads without vision", status == 200 and len(sections) >= 4, ",".join(sections))

status, grid = call("music_beat_grid", {"ref": music_item["id"]})
check("music_beat_grid", status == 200 and grid["bpm"] > 0 and grid["beats"], f"{grid['bpm']}bpm, {len(grid['beats'])} beats")

status, clip = call("cut_media", {"ref": video_item["id"], "start_seconds": 0.5, "end_seconds": 2.0})
check("cut_media", status == 200 and clip["duration_seconds"] > 1.0, f"{clip['duration_seconds']}s -> {clip['asset_id']}")

status, again = call("inspect_media", {"ref": clip["asset_id"]})
check("chained call by asset_id", status == 200 and again["has_video"], f"{again['width']}x{again['height']}")

status, parts = call("split_media", {"ref": video_item["id"], "timestamps": [1.0, 2.0]})
check("split_media", status == 200 and len(parts) == 3, f"{[p['index'] for p in parts]}")

status, joined = call("join_media", {"refs": [parts[0]["asset_id"], parts[1]["asset_id"]]})
check("join_media", status == 200 and joined["duration_seconds"] > 1.0, f"{joined['duration_seconds']}s")

status, mixed = call(
    "audio_mix",
    {
        "tracks": [
            {"ref": video_item["id"], "role": "voice"},
            {"ref": music_item["id"], "role": "music", "loop": True, "gain_db": -8},
        ],
        "duration_seconds": 4.0,
    },
)
check("audio_mix ducks the bed", status == 200 and mixed["ducked"] is True, f"{mixed['duration_seconds']}s, {mixed['loudness_lufs']} LUFS")

status, faded = call("audio_fade", {"ref": music_item["id"], "fade_in_seconds": 1.0, "fade_out_seconds": 2.0})
check("audio_fade", status == 200 and faded["duration_seconds"] > 5.0, f"{faded['duration_seconds']}s")

status, frame = call("extract_frame_image", {"ref": video_item["id"], "at_seconds": 1.0})
check("extract_frame_image", status == 200 and frame["size_bytes"] > 0, f"{frame['size_bytes']}B")

status, sheet = call("media_contact_sheet", {"ref": video_item["id"], "count": 6, "columns": 3})
check("media_contact_sheet", status == 200 and len(sheet["timestamps"]) == 6, f"{sheet['timestamps']}")

status, composed = call(
    "compose_images",
    {
        "base": photo_item["id"],
        "layers": [{"ref": photo_item["id"], "x": "bottom-right", "y": "bottom-right", "scale": 0.5, "blend": "screen"}],
    },
)
check("compose_images", status == 200 and composed["layer_count"] == 1, f"{composed['width']}x{composed['height']}")

status, collage = call("collage_images", {"refs": [photo_item["id"], photo_item["id"]], "columns": 2, "captions": ["a", "b"]})
check("collage_images", status == 200 and collage["rows"] == 1, f"{collage['width']}x{collage['height']}")

status, loudness = call("media_loudness", {"ref": music_item["id"], "target_lufs": -14})
check("media_loudness", status == 200 and loudness["integrated_lufs"] is not None, f"{loudness['integrated_lufs']} LUFS")

status, body = call("describe_media", {"ref": "does-not-exist"})
check("missing ref maps to 404", status == 404, body.get("detail", "")[:60])

status, body = call("cut_media", {"ref": video_item["id"]})
check(
    "missing required arg maps to 422",
    status == 422 and "end_seconds" in str(body.get("detail")),
    str(body.get("detail"))[:60],
)
status, body = call("media_scene_cuts", {"ref": video_item["id"], "threshold": "loud"})
check("wrong type maps to 422", status == 422, str(body.get("detail"))[:60])

asset = urllib.request.urlopen(f"{BASE}{clip['url']}", timeout=30)
check("edited asset served over HTTP", asset.status == 200, f"{clip['url']} {asset.headers.get('content-type')}")

failed = [name for name, ok, _ in CHECKS if not ok]
print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} live checks passed")
if failed:
    print("failed:", failed)
shutil.rmtree(WORK, ignore_errors=True)
sys.exit(1 if failed else 0)
