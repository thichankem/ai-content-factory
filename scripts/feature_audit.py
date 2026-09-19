"""Functional audit: drive every agent tool and HTTP surface, measure each call.

Unlike ``scripts/smoke.py`` (which asserts one happy path end to end), this
script *inventories* the feature surface. It calls all 110 ``/tools/call``
tools plus the HTTP routes the tools do not cover, records wall-clock time and
outcome for each, and writes a report an operator can hand to the next agent.

Groups run fastest-first except ``vision``, which runs first on purpose: the
provider-backed features are the ones worth knowing about before anything else.

Usage::

    python scripts/feature_audit.py                     # spawns its own server
    python scripts/feature_audit.py --port 8180          # reuse a server
    python scripts/feature_audit.py --groups vision,image
    python scripts/feature_audit.py --json docs/feature-audit.json \
        --md docs/FEATURE-AUDIT.md

Fixtures are written under ``storage/uploads/`` (gitignored); nothing else in
the tree is modified.
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import math
import os
import random
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import wave
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
FIXTURE_DIR = ROOT / "storage" / "uploads" / "feature-audit"

BASE = "http://127.0.0.1:8188"
RECORDS: list[dict[str, Any]] = []


# --------------------------------------------------------------------------- #
# probe plumbing
# --------------------------------------------------------------------------- #


@dataclass
class Probe:
    """One call to measure."""

    group: str
    name: str
    payload: dict[str, Any] | None = None
    path: str = "/tools/call"
    method: str = "POST"
    expect: tuple[int, ...] = (200,)
    needs: str = "local"
    note: str = ""
    #: Human label for the report when the called target is not descriptive.
    label: str = ""
    digest: tuple[str, ...] = ()
    #: ``{field: str}`` or ``{field: (filename, bytes)}`` for the /studio/* routes,
    #: which take multipart uploads while /tools/call takes base64 JSON.
    multipart: dict[str, Any] | None = None
    # Filled in when the probe runs; later probes may read it (dependency chain).
    result: dict[str, Any] = field(default_factory=dict)


def _encode_multipart(fields: dict[str, Any]) -> tuple[bytes, str]:
    """Build a multipart/form-data body; a list value repeats the field."""
    boundary = "----feature-audit-boundary"
    chunks: list[bytes] = []
    for name, value in fields.items():
        entries = value if isinstance(value, list) else [value]
        for entry in entries:
            if isinstance(entry, tuple):
                filename, payload = entry
                head = (
                    f"--{boundary}\r\nContent-Disposition: form-data; "
                    f'name="{name}"; filename="{filename}"\r\n'
                    "Content-Type: application/octet-stream\r\n\r\n"
                )
                chunks.append(head.encode() + payload + b"\r\n")
            else:
                head = (
                    f"--{boundary}\r\nContent-Disposition: form-data; "
                    f'name="{name}"\r\n\r\n'
                )
                chunks.append(head.encode() + str(entry).encode() + b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), boundary


def _request(
    method: str,
    path: str,
    body: dict[str, Any] | None,
    timeout: float,
    multipart: dict[str, Any] | None = None,
) -> tuple[int, bytes, float]:
    if multipart is not None:
        data, boundary = _encode_multipart(multipart)
        content_type = f"multipart/form-data; boundary={boundary}"
    else:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        content_type = "application/json"
    safe_path = (
        urllib.parse.quote(path, safe="/?=&%:,@!$'()*+;[]") if " " in path else path
    )
    request = urllib.request.Request(BASE + safe_path, data=data, method=method)
    if data is not None:
        request.add_header("Content-Type", content_type)
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read(), time.perf_counter() - started
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, exc.read(), time.perf_counter() - started
        except OSError:  # a big body the server refused without reading
            return exc.code, b"(no body)", time.perf_counter() - started


def _summarize(body: Any, keys: tuple[str, ...]) -> str:
    """One short line describing a successful response."""
    if not isinstance(body, dict):
        if isinstance(body, list):
            return f"list[{len(body)}]"
        return str(body)[:60]
    picked = []
    for key in keys:
        if key in body:
            value = body[key]
            if isinstance(value, (list, dict)):
                picked.append(f"{key}={len(value)}")
            elif isinstance(value, str) and len(value) > 40:
                picked.append(f"{key}={value[:37]}...")
            else:
                picked.append(f"{key}={value}")
    if not picked:
        picked = [f"keys={','.join(list(body)[:6])}"]
    return " ".join(picked)


def run_probe(probe: Probe, timeout: float = 180.0) -> dict[str, Any]:
    status, raw, seconds = _request(
        probe.method, probe.path, probe.payload, timeout, probe.multipart
    )
    text = raw.decode("utf-8", "replace")
    record: dict[str, Any] = {
        "group": probe.group,
        "name": probe.label or probe.name,
        "target": probe.name,
        "needs": probe.needs,
        "note": probe.note,
        "status": status,
        "seconds": round(seconds, 3),
        "expect": list(probe.expect),
    }
    body: Any = None
    try:
        body = json.loads(text)
    except ValueError:
        body = text[:400]
    if status in probe.expect:
        record["outcome"] = "pass"
        record["detail"] = _summarize(body, probe.digest)
        if isinstance(body, dict):
            probe.result = body
    else:
        detail = body.get("detail") if isinstance(body, dict) else body
        record["outcome"] = "fail"
        record["detail"] = str(detail)[:300]
        if isinstance(detail, dict):
            record["detail"] = json.dumps(detail)[:300]
    RECORDS.append(record)
    mark = "ok  " if record["outcome"] == "pass" else "FAIL"
    print(
        f"  [{mark}] {record['seconds']:7.3f}s {record['name']}"
        f"{'' if record['outcome'] == 'pass' else ' -> ' + str(record['status'])}"
        + (f"  {record['detail']}" if record["outcome"] == "pass" else "")
    )
    if record["outcome"] != "pass":
        print(f"           {record['detail']}")
    return record


def tool(group: str, name: str, args: dict[str, Any] | None = None, **kw: Any) -> Probe:
    return Probe(
        group=group,
        name=f"tool:{name}",
        payload={"tool": name, "args": args or {}},
        **kw,
    )


def http(
    group: str,
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    **kw: Any,
) -> Probe:
    return Probe(
        group=group,
        name=f"{method} {path}",
        method=method,
        path=path,
        payload=body,
        **kw,
    )


def upload(
    group: str,
    method: str,
    path: str,
    label: str,
    fields: dict[str, Any],
    **kw: Any,
) -> Probe:
    """A multipart call to one of the /studio/* routes."""
    return Probe(
        group=group,
        name=f"{label} [{method} {path}]",
        method=method,
        path=path,
        multipart=fields,
        **kw,
    )


# ----------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #


def synthetic_png(width: int = 480, height: int = 270) -> bytes:
    """A crisp test card: colour blocks, a circle and a label."""
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (width, height), (18, 24, 38))
    draw = ImageDraw.Draw(image)
    for index, colour in enumerate(
        [(220, 60, 60), (240, 170, 40), (60, 190, 120), (60, 130, 220), (150, 90, 210)]
    ):
        band = width // 5
        draw.rectangle(
            [index * band, 0, (index + 1) * band - 4, height // 3], fill=colour
        )
    draw.ellipse(
        [width // 2 - 60, height // 2 - 40, width // 2 + 60, height // 2 + 40],
        fill=(250, 250, 250),
    )
    draw.rectangle(
        [20, height - 50, width - 20, height - 16],
        fill=(10, 12, 20),
        outline=(90, 90, 120),
    )
    draw.text((32, height - 42), "AI CONTENT FACTORY", fill=(240, 240, 240))
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


def audit_screenshot() -> bytes:
    """A real screenshot from ``picture/`` as the vision-analysis fixture."""
    from PIL import Image

    candidates = sorted((ROOT / "picture").rglob("*.png"))
    if not candidates:
        return synthetic_png()
    image = Image.open(candidates[1] if len(candidates) > 1 else candidates[0])
    image = image.convert("RGB")
    if image.width > 1024:
        ratio = 1024 / image.width
        image = image.resize((1024, max(1, int(image.height * ratio))))
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=85)
    return buffer.getvalue()


def speech_like_wav(seconds: float = 3.0, rate: int = 44100) -> bytes:
    """A voiced-sounding tone with room noise, as WAV bytes."""
    rng = random.Random(7)
    frames = bytearray()
    samples = int(seconds * rate)
    for index in range(samples):
        t = index / rate
        # 210 Hz fundamental + harmonics, amplitude-wobbled like speech, + noise
        envelope = 0.55 + 0.45 * math.sin(2 * math.pi * 3.1 * t)
        value = (
            0.5 * math.sin(2 * math.pi * 210 * t)
            + 0.28 * math.sin(2 * math.pi * 420 * t)
            + 0.12 * math.sin(2 * math.pi * 630 * t)
        ) * envelope
        value += rng.uniform(-0.03, 0.03)
        frames += struct.pack("<h", int(max(-1.0, min(1.0, value)) * 32000))
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(bytes(frames))
    return buffer.getvalue()


def tone_wav(freq: float, seconds: float = 3.0, rate: int = 44100) -> bytes:
    frames = bytearray()
    for index in range(int(seconds * rate)):
        frames += struct.pack(
            "<h", int(0.6 * 32000 * math.sin(2 * math.pi * freq * index / rate))
        )
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(bytes(frames))
    return buffer.getvalue()


def make_mp4(path: Path) -> Path:
    """Render a small real MP4 (video + audio) with ffmpeg."""
    if path.is_file():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    png = path.with_suffix(".png")
    png.write_bytes(synthetic_png(640, 360))
    command = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-loop",
        "1",
        "-i",
        str(png),
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:duration=4",
        "-t",
        "4",
        "-r",
        "25",
        "-pix_fmt",
        "yuv420p",
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        "-shortest",
        str(path),
    ]
    subprocess.run(command, check=True, capture_output=True)
    return path


def b64_of(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


# --------------------------------------------------------------------------- #
# probe groups — ordered as the operator asked: AI vision first, then fast → slow
# --------------------------------------------------------------------------- #


def group_vision(ctx: dict[str, Any]) -> list[Probe]:
    shot = ctx["shot_b64"]
    chart = ctx["chart_b64"]
    return [
        tool(
            "vision",
            "analyze_image",
            {"image_b64": shot},
            needs="local",
            note="Pixel-statistics analysis of a real 1024px screenshot",
            digest=("width", "height", "dominant_colors", "tags", "description"),
        ),
        tool(
            "vision",
            "analyze_image",
            {"image_b64": chart},
            needs="local",
            note="Same tool on the synthetic colour test card",
            digest=("width", "height", "tags"),
        ),
        tool(
            "vision",
            "suggest_image_edits",
            {"image_b64": shot},
            needs="local",
            note="Histogram-driven edit suggestions + recommended op list",
            digest=("suggestions", "ops", "summary"),
        ),
        tool(
            "vision",
            "describe_image_op",
            {"name": "tone"},
            needs="local",
            note="Catalogue lookup only — the honest baseline for the vision pair",
            digest=("name", "description", "params"),
        ),
        tool(
            "vision",
            "describe_media",
            {"ref": ctx["local_video_ref"], "include": ["vision"]},
            needs="provider+ffmpeg",
            # ``vision`` is not a describe section. Asking for it used to return
            # the default report with no warning (a caller thinks it got a
            # vision pass); it is now refused, naming the valid sections.
            expect=(422,),
            note="Unknown section 'vision' must be refused, not silently ignored",
            digest=("detail",),
        ),
        tool(
            "vision",
            "media_scene_cuts",
            {"ref": ctx["local_video_ref"]},
            needs="ffmpeg",
            note="Local scene-change detection (the non-AI half of understanding)",
            digest=("cuts", "count"),
        ),
        tool(
            "vision",
            "suggest_video_edits",
            {"project_id": ctx["project_id"]},
            needs="provider",
            note="Vision/LLM edit suggestions for the built timeline",
            digest=("suggestions", "summary"),
        ),
        tool(
            "vision",
            "ai_assist",
            {"project_id": ctx["project_id"], "fit": True, "beat": True, "bpm": 120},
            needs="provider",
            note="AI timeline assist (fit-to-duration + beat cut)",
            digest=("applied", "summary"),
        ),
        tool(
            "vision",
            "describe_media",
            {"ref": ctx["image_ref"], "include": ["vision"]},
            needs="provider",
            expect=(422,),
            note="Unknown section over a still image — same refusal",
            digest=("detail",),
        ),
        tool(
            "vision",
            "media_palette",
            {"ref": ctx["image_ref"]},
            needs="local",
            note="Local colour extraction — should work with no provider",
            digest=("colors", "palette", "count"),
        ),
        upload(
            "vision",
            "POST",
            "/studio/image/analyze",
            "studio: analyze image",
            {"file": ("chart.png", ctx["chart_bytes"])},
            needs="local",
            note="Multipart twin of analyze_image",
            digest=("summary", "details"),
        ),
        upload(
            "vision",
            "POST",
            "/studio/image/suggest",
            "studio: suggest image edits",
            {"file": ("shot.jpg", ctx["shot_bytes"])},
            needs="local",
            note="Multipart twin of suggest_image_edits (the vision-backed one)",
            digest=("suggestions", "count"),
        ),
    ]


def group_catalog(ctx: dict[str, Any]) -> list[Probe]:
    return [
        tool("catalog", "agent_catalog", {}, digest=("categories", "count", "tools")),
        tool("catalog", "list_script_styles", {}, digest=("styles", "count")),
        tool("catalog", "image_op_catalog", {}, digest=("ops", "count", "categories")),
        tool("catalog", "image_presets", {}, digest=("presets", "count")),
        tool("catalog", "video_effect_catalog", {}, digest=("effects", "count")),
        tool("catalog", "video_operation_catalog", {}, digest=("operations", "count")),
        tool("catalog", "audio_effect_catalog", {}, digest=("effects", "count")),
        tool("catalog", "audio_operation_catalog", {}, digest=("operations", "count")),
        tool("catalog", "ai_audio_catalog", {}, digest=("capabilities", "count")),
        tool("catalog", "stem_catalog", {}, digest=("stems", "count")),
        tool("catalog", "sfx_catalog", {}, digest=("sfx", "count")),
        tool("catalog", "voice_presets", {}, digest=("presets", "count")),
        tool("catalog", "seo_rules", {}, digest=("rules", "count", "platforms")),
        tool(
            "catalog",
            "resource_status",
            {},
            digest=("cpu", "gpu", "memory", "encoders"),
        ),
        tool("catalog", "resource_explain", {}, digest=("summary", "kinds")),
        tool(
            "catalog",
            "describe_video_operation",
            {"name": "split_scene"},
            digest=("name", "description"),
        ),
        tool(
            "catalog",
            "describe_audio_operation",
            {"name": "audio_trim"},
            digest=("name", "description"),
        ),
        tool("catalog", "list_projects", {}, digest=("projects", "count")),
        tool("catalog", "list_media", {}, digest=("items", "count", "media")),
        tool("catalog", "list_kbs", {}, digest=("knowledge_bases", "count")),
    ]


def group_image(ctx: dict[str, Any]) -> list[Probe]:
    return [
        tool(
            "image",
            "edit_image",
            {
                "image_b64": ctx["chart_b64"],
                "ops": [
                    {"name": "tone", "params": {"brightness": 1.15, "contrast": 1.1}},
                    {"name": "filter", "params": {"preset": "noir"}},
                ],
                "format": "jpeg",
            },
            note="Two-op pipeline with a filter preset",
            digest=("asset_id", "url", "width", "height", "format"),
        ),
        tool(
            "image",
            "edit_image",
            {
                "image_b64": ctx["chart_b64"],
                "preset": "thumbnail",
                "format": "png",
            },
            note="Preset-driven edit",
            digest=("asset_id", "url", "width", "height"),
        ),
        tool(
            "image",
            "edit_image",
            {
                "image_b64": ctx["chart_b64"],
                "ops": [{"name": "resize", "params": {"width": 320}}],
            },
            note="Explicit no-op guard: does width alone work?",
            digest=("asset_id", "width", "height"),
        ),
        tool(
            "image",
            "batch_edit_image",
            {
                "images_b64": [ctx["chart_b64"], ctx["shot_b64"]],
                "ops": [{"name": "filter", "params": {"preset": "sepia"}}],
            },
            note="Batch path — two very different payload sizes",
            digest=("assets", "count", "items"),
        ),
        tool(
            "image",
            "compose_images",
            {
                "base": ctx["chart_b64"],
                "layers": [
                    {
                        "image_b64": ctx["shot_b64"],
                        "x": 20,
                        "y": 20,
                        "width": 200,
                        "opacity": 0.8,
                    }
                ],
                "format": "png",
            },
            # ``base`` takes a *ref*. Passing base64 used to answer
            # "Nothing named 'iVBORw0KGgo…'" — 300 characters of the payload
            # echoed back and no hint about what to do instead. It now names the
            # mistake and the tools that do take bytes.
            expect=(422,),
            note="base64 passed as a ref must be explained, not echoed",
            digest=("detail",),
        ),
        tool(
            "image",
            "collage_images",
            {
                "refs": [ctx["image_ref"], ctx["image_ref_2"]],
                "columns": 2,
                "captions": ["A", "B"],
            },
            note="Collage from library refs with captions",
            digest=("asset_id", "url", "width", "height"),
        ),
        tool(
            "image",
            "apply_video_effect",
            {
                "image_b64": ctx["chart_b64"],
                "name": "glitch",
                "params": {},
                "format": "png",
            },
            note="Video-effect engine applied to a still",
            digest=("asset_id", "url", "effect", "params"),
        ),
        tool(
            "image",
            "begin_image_session",
            {"image_b64": ctx["chart_b64"]},
            note="Image session: begin",
            digest=("session_id", "width", "height", "ops"),
        ),
        Probe(
            "image",
            "tool:edit_image_session",
            path="/tools/call",
            method="POST",
            payload={},
            note="filled at runtime",
            needs="local",
        ),
        Probe(
            "image",
            "tool:undo_image_session",
            path="/tools/call",
            method="POST",
            payload={},
            note="filled at runtime",
            needs="local",
        ),
        Probe(
            "image",
            "tool:redo_image_session",
            path="/tools/call",
            method="POST",
            payload={},
            note="filled at runtime",
            needs="local",
        ),
        Probe(
            "image",
            "tool:image_session_state",
            path="/tools/call",
            method="POST",
            payload={},
            note="filled at runtime",
            needs="local",
        ),
        tool(
            "image",
            "media_contact_sheet",
            {"ref": ctx["local_video_ref"], "count": 6, "columns": 3},
            needs="ffmpeg",
            note="Frame grid from a real video",
            digest=("asset_id", "url", "width", "height"),
        ),
        tool(
            "image",
            "extract_frame_image",
            {"ref": ctx["local_video_ref"], "at": 1.5},
            needs="ffmpeg",
            note="Single frame extraction",
            digest=("asset_id", "url", "width", "height"),
        ),
        tool(
            "image",
            "edit_image",
            {"image_b64": "not-an-image", "ops": []},
            expect=(400, 404, 422),
            note="Negative path: garbage image bytes",
        ),
        tool(
            "image",
            "edit_image",
            {"image_b64": ctx["chart_b64"], "ops": [{"name": "magic"}]},
            expect=(400, 404, 422),
            note="Negative path: unknown op name",
        ),
        upload(
            "image",
            "POST",
            "/studio/image/edit",
            "studio: edit image",
            {
                "file": ("chart.png", ctx["chart_bytes"]),
                "ops": json.dumps([{"name": "filter", "params": {"preset": "cool"}}]),
                "format": "jpeg",
            },
            note="Multipart edit with ops as a JSON string",
            digest=("asset_id", "url"),
        ),
        upload(
            "image",
            "POST",
            "/studio/image/batch",
            "studio: batch edit",
            {
                "files": [("a.png", ctx["chart_bytes"]), ("b.png", ctx["chart_bytes"])],
                "preset": "noir",
            },
            note="Multipart batch over two files",
            digest=("assets", "count"),
        ),
        upload(
            "image",
            "POST",
            "/studio/image/session/begin",
            "studio: begin session",
            {"file": ("chart.png", ctx["chart_bytes"])},
            digest=("session_id",),
        ),
        http("image", "GET", "/studio/image/ops", {}),
        http("image", "GET", "/studio/image/presets", {}),
        http("image", "POST", "/studio/image/describe-op", None, expect=(200, 422)),
        http("image", "GET", "/studio/video/ops", {}),
        http("image", "GET", "/studio/video/effects", {}),
        http("image", "POST", "/studio/video/describe-op", None, expect=(200, 422)),
    ]


def group_audio(ctx: dict[str, Any]) -> list[Probe]:
    voice = ctx["voice_b64"]
    music = ctx["music_b64"]
    return [
        tool(
            "audio",
            "analyze_audio",
            {"audio_b64": voice},
            note="Local analysis: loudness, silence, SNR, speech estimate",
            digest=("duration_seconds", "loudness", "noise_floor", "rms", "speech"),
        ),
        tool(
            "audio",
            "describe_audio",
            {"audio_b64": voice},
            note="Human-readable description of the same",
            digest=("summary", "loudness", "duration"),
        ),
        tool(
            "audio",
            "apply_audio_effect",
            {"audio_b64": voice, "name": "telephone", "params": {}, "format": "mp3"},
            note="Band effect through the fixed RBJ filters",
            digest=("asset_id", "url", "effect", "duration"),
        ),
        tool(
            "audio",
            "apply_audio_effect",
            {
                "audio_b64": voice,
                "name": "reverb",
                "params": {"room": 0.6},
                "format": "wav",
            },
            note="Time-domain effect with a param",
            digest=("asset_id", "url", "effect"),
        ),
        tool(
            "audio",
            "apply_audio_mastering",
            {"audio_b64": voice, "format": "mp3"},
            note="Full mastering chain",
            digest=("asset_id", "url", "steps", "loudness"),
        ),
        tool(
            "audio",
            "suggest_audio_mastering",
            {"audio_b64": voice},
            needs="provider",
            note="Provider-backed mastering advice",
            digest=("suggestions", "steps"),
        ),
        tool(
            "audio",
            "separate_audio_stems",
            {"audio_b64": voice, "num": 2, "format": "wav"},
            needs="local(demucs optional)",
            note="Stem split — no demucs installed, so the DSP fallback runs",
            digest=("stems", "count", "engine", "assets"),
        ),
        tool(
            "audio",
            "enhance_voice",
            {"audio_b64": voice, "preset": "podcast", "format": "wav"},
            note="Voice cleanup preset",
            digest=("asset_id", "url", "preset", "steps"),
        ),
        tool(
            "audio",
            "duck_music",
            {"voice_b64": voice, "music_b64": music, "duck_db": -12},
            note="Sidechain ducking of music under voice",
            digest=("asset_id", "url", "duck_db", "duration"),
        ),
        tool(
            "audio",
            "audio_trim",
            {"ref": ctx["edited_audio_ref"], "start_seconds": 0.4, "end_seconds": 1.8},
            note="Media-op chain: trim an edited asset",
            digest=("asset_id", "url", "duration"),
        ),
        tool(
            "audio",
            "audio_fade",
            {"ref": ctx["edited_audio_ref"], "fade_in": 0.5, "fade_out": 0.7},
        ),
        tool(
            "audio",
            "audio_loop",
            {"ref": ctx["edited_audio_ref"], "duration_seconds": 6},
        ),
        tool(
            "audio",
            "audio_normalize",
            {"ref": ctx["edited_audio_ref"], "target_lufs": -14},
        ),
        tool("audio", "audio_retime", {"ref": ctx["edited_audio_ref"], "factor": 1.25}),
        tool(
            "audio",
            "audio_mix",
            {
                "tracks": [
                    {"ref": ctx["edited_audio_ref"], "gain_db": -6},
                    {"ref": ctx["edited_audio_ref"], "gain_db": -3},
                ],
                "duration_seconds": 2,
            },
            note="Mix two tracks with gains",
            digest=("asset_id", "url", "duration"),
        ),
        tool(
            "audio", "audio_denoise", {"ref": ctx["edited_audio_ref"], "strength": 0.6}
        ),
        tool(
            "audio",
            "music_beat_grid",
            {"ref": ctx["music_ref"], "bpm": 120},
            note="Beat grid over a real music file",
            digest=("beats", "count", "bpm"),
        ),
        tool(
            "audio",
            "synthesize_sfx",
            {"name": "whoosh", "params": {"duration": 1.2}, "format": "wav"},
            note="Procedural SFX synthesis",
            digest=("asset_id", "url", "duration"),
        ),
        tool(
            "audio",
            "media_loudness",
            {"ref": ctx["local_video_ref"]},
            needs="ffmpeg",
            note="Integrated loudness of a real video's audio",
            digest=("loudness", "lufs", "duration"),
        ),
        tool(
            "audio",
            "media_silence",
            {"ref": ctx["local_video_ref"]},
            needs="ffmpeg",
            note="Silence detection over the video",
            digest=("silences", "count"),
        ),
        tool(
            "audio",
            "extract_audio_track",
            {"ref": ctx["local_video_ref"], "format": "wav"},
            needs="ffmpeg",
            note="Audio demux from a real video",
            digest=("asset_id", "url", "duration"),
        ),
        tool(
            "audio",
            "dub_audio",
            {
                "audio_b64": voice,
                "target_text": "Xin chào, đây là bản lồng tiếng thử nghiệm.",
                "lang": "vi",
            },
            needs="provider+ml-adapter",
            note="Dubbing: transcribe → translate → re-voice",
        ),
        tool(
            "audio",
            "voice_clone",
            {"audio_b64": voice, "ref_voice": voice},
            needs="provider+ml-adapter",
            note="Voice cloning — ref_voice is documented as base64, no XTTS installed",
        ),
        upload(
            "audio",
            "POST",
            "/studio/audio/analyze",
            "studio: analyze audio",
            {"file": ("voice.wav", ctx["voice_bytes"])},
            digest=("duration_seconds", "loudness"),
        ),
        upload(
            "audio",
            "POST",
            "/studio/audio/describe",
            "studio: describe audio",
            {"file": ("voice.wav", ctx["voice_bytes"])},
            digest=("summary",),
        ),
        upload(
            "audio",
            "POST",
            "/studio/audio/effect",
            "studio: apply audio effect",
            {
                "file": ("voice.wav", ctx["voice_bytes"]),
                "name": "telephone",
                "format": "mp3",
            },
            digest=("asset_id", "url"),
        ),
        upload(
            "audio",
            "POST",
            "/studio/audio/stems",
            "studio: stems",
            {"file": ("voice.wav", ctx["voice_bytes"]), "num": "2", "format": "wav"},
            digest=("stems", "count"),
        ),
        upload(
            "audio",
            "POST",
            "/studio/audio/mastering",
            "studio: suggest mastering",
            {"file": ("voice.wav", ctx["voice_bytes"])},
            digest=("suggestions", "count"),
        ),
        upload(
            "audio",
            "POST",
            "/studio/voice/enhance",
            "studio: enhance voice",
            {
                "file": ("voice.wav", ctx["voice_bytes"]),
                "preset": "podcast",
                "format": "wav",
            },
            digest=("asset_id", "url"),
        ),
        http("audio", "GET", "/studio/audio/ops", {}),
        http("audio", "GET", "/studio/audio/effects", {}),
        http("audio", "GET", "/studio/audio/ai", {}),
        http("audio", "GET", "/studio/audio/stems", {}),
        http("audio", "GET", "/studio/audio/sfx", {}),
        http("audio", "GET", "/studio/voice/presets", {}),
    ]


def group_media(ctx: dict[str, Any]) -> list[Probe]:
    video = ctx["local_video_ref"]
    return [
        tool(
            "media",
            "inspect_media",
            {"ref": video},
            needs="ffprobe",
            note="Probe a real video fixture (video + audio streams)",
            digest=("has_video", "has_audio", "duration_seconds", "width", "height"),
        ),
        tool(
            "media",
            "inspect_media",
            {"ref": ctx["video_ref"]},
            needs="ffprobe",
            # A media library accumulates what earlier versions wrote into it —
            # including HTML pages saved as ``.mp4`` by the pre-fix download
            # path. Probing one must answer 422 ("cannot read this file"), not
            # 500, and must not pretend the item is fine.
            note="Probe a *library* item: audio-only kind mismatch, or unreadable",
            expect=(200, 404, 422),
            digest=("kind", "has_video", "has_audio", "duration_seconds", "detail"),
        ),
        tool(
            "media",
            "get_media",
            {"media_id": ctx["media_id"]},
            digest=("id", "name", "kind", "path"),
        ),
        tool(
            "media",
            "cut_media",
            {"ref": video, "start_seconds": 0.5, "end_seconds": 2.0, "reencode": False},
            needs="ffmpeg",
            note="Stream-copy cut (no re-encode)",
            digest=("asset_id", "url", "duration"),
        ),
        tool(
            "media",
            "cut_media",
            {"ref": video, "start_seconds": 0.5, "end_seconds": 2.0, "reencode": True},
            needs="ffmpeg",
            note="Re-encoding cut",
            digest=("asset_id", "url", "duration"),
        ),
        tool(
            "media",
            "split_media",
            {"ref": video, "timestamps": [1.0, 2.5]},
            needs="ffmpeg",
            note="Split into three segments",
            digest=("assets", "count", "parts"),
        ),
        tool(
            "media",
            "join_media",
            {"refs": [ctx["clip_a_ref"], ctx["clip_b_ref"]], "reencode": True},
            needs="ffmpeg",
            note="Concat two generated clips",
            digest=("asset_id", "url", "duration"),
        ),
    ]


def group_timeline(ctx: dict[str, Any]) -> list[Probe]:
    pid = ctx["project_id"]
    scene = ctx["scene_id"]
    other = ctx["scene_id_2"]
    # build_video_project runs last on purpose: it replaces every scene id, so
    # every probe before it can address the scenes the fixtures captured.
    return [
        tool(
            "timeline",
            "timeline_report",
            {"project_id": pid},
            digest=("score", "issues", "duration"),
        ),
        tool(
            "timeline",
            "render_plan",
            {"project_id": pid},
            digest=("width", "height", "fps", "steps", "subtitles"),
        ),
        tool(
            "timeline",
            "describe_video_timeline",
            {"project_id": pid},
            digest=("scenes", "summary"),
        ),
        tool(
            "timeline",
            "set_scene_speed",
            {"project_id": pid, "scene_id": scene, "speed": 0.75},
        ),
        tool(
            "timeline",
            "reverse_scene",
            {"project_id": pid, "scene_id": scene, "reverse": True},
        ),
        tool(
            "timeline",
            "trim_scene",
            {"project_id": pid, "scene_id": scene, "trim_start": 0.3, "trim_end": 2.2},
        ),
        tool(
            "timeline",
            "set_scene_audio",
            {
                "project_id": pid,
                "scene_id": scene,
                "volume": 1.4,
                "fade_in": 0.3,
                "fade_out": 0.5,
            },
        ),
        tool(
            "timeline", "split_scene", {"project_id": pid, "scene_id": scene, "at": 0.8}
        ),
        tool("timeline", "duplicate_scene", {"project_id": pid, "scene_id": scene}),
        tool(
            "timeline",
            "move_scene",
            {"project_id": pid, "scene_id": scene, "to_index": 1},
        ),
        tool(
            "timeline",
            "bulk_update_scenes",
            {
                "project_id": pid,
                "scene_ids": [scene, other],
                "patch": {"grade": "noir"},
            },
        ),
        tool(
            "timeline",
            "set_keyframes",
            {
                "project_id": pid,
                "scene_id": scene,
                "keyframes": [{"at": 0.0, "zoom": 1.0}, {"at": 1.0, "zoom": 1.2}],
            },
        ),
        tool(
            "timeline",
            "add_marker",
            {"project_id": pid, "time_seconds": 4.0, "label": "beat"},
        ),
        tool("timeline", "merge_scene", {"project_id": pid, "scene_id": scene}),
        tool("timeline", "delete_scene", {"project_id": pid, "scene_id": other}),
        tool(
            "timeline",
            "auto_cut_to_beat",
            {"project_id": pid, "music_ref": ctx["music_ref"], "bpm": 120},
            needs="ffmpeg",
        ),
        tool(
            "timeline",
            "trim_scene",
            {"project_id": pid, "scene_id": "deadbeef", "trim_start": 1.0},
            expect=(404,),
            note="Negative path: stale scene id must 404 with a human message",
        ),
        tool(
            "timeline",
            "get_project",
            {"project_id": "does-not-exist"},
            expect=(404,),
            note="Negative path: unknown project",
        ),
        http("timeline", "GET", f"/projects/{pid}/timeline/report"),
        http("timeline", "GET", f"/projects/{pid}/timeline/describe"),
        http("timeline", "GET", f"/projects/{pid}/render-plan"),
        http("timeline", "POST", f"/projects/{pid}/timeline/normalize", {}),
        http(
            "timeline",
            "POST",
            "/timeline/command",
            {
                "project": ctx["project_body"],
                "text": "trim the first scene to 2 seconds",
            },
            expect=(200, 422),
            note="Sends the whole project object, as the model requires",
        ),
        http("timeline", "GET", f"/projects/{pid}/timeline/suggest"),
        tool(
            "timeline",
            "build_video_project",
            {"project_id": pid},
            note="Rebuild: it replaces the scene ids, so agent caches go stale",
            digest=("video_project", "scenes"),
        ),
    ]


def group_script(ctx: dict[str, Any]) -> list[Probe]:
    pid = ctx["project_id"]
    return [
        tool(
            "script",
            "update_script",
            {
                "project_id": pid,
                "script": (
                    "[Hook]\nĐại dương rút lui trước khi cơn sóng thần ập tới.\n\n"
                    "[Turn]\nKhông ai trên bãi biển hiểu điều gì đang tới.\n\n"
                    "[Outro]\nBa đại dương gợn sóng trong cùng một ngày."
                ),
                "source_rights_confirmed": True,
            },
            expect=(200, 409),
            note="409 once generation started is the state machine working",
        ),
        tool(
            "script",
            "analyze_script",
            {"project_id": pid},
            digest=("score", "issues", "readability", "words"),
        ),
        tool(
            "script",
            "export_brief",
            {"project_id": pid},
            digest=("markdown", "brief", "length"),
        ),
        http("script", "POST", f"/projects/{pid}/script/analyze", {}),
        http("script", "GET", f"/projects/{pid}/brief.md"),
    ]


def group_seo(ctx: dict[str, Any]) -> list[Probe]:
    pid = ctx["project_id"]
    pack = {
        "title": "Sóng thần Ấn Độ Dương 2004: 20 phút không ai kịp chạy",
        "description": "Phân tích sự kiện 26/12/2004, thiệt hại và bài học cảnh báo.",
        "tags": ["sóng thần", "thiên tai", "Ấn Độ Dương", "cảnh báo"],
    }
    return [
        tool(
            "seo",
            "seo_score",
            {"platform": "youtube", "pack": pack},
            digest=("score", "issues", "grade"),
        ),
        tool(
            "seo",
            "seo_optimize",
            {"platform": "youtube", "pack": pack},
            needs="provider",
            digest=("optimized", "changes", "pack"),
        ),
        tool(
            "seo",
            "seo_score_project",
            {"project_id": pid},
            digest=("score", "issues", "platform"),
        ),
        tool(
            "seo",
            "seo_keywords",
            {"keywords": ["sóng thần 2004", "tsunami indian ocean"], "competitors": []},
            digest=("clusters", "keywords", "count"),
        ),
        tool(
            "seo",
            "seo_ab_plan",
            {"baseline_rate": 0.042},
            digest=("arms", "count", "sample_size"),
        ),
        tool(
            "seo",
            "seo_ab_evaluate",
            {
                "arms": [
                    {"name": "A", "views": 1000, "clicks": 42},
                    {"name": "B", "views": 1000, "clicks": 58},
                ]
            },
            digest=("winner", "confidence", "lift"),
        ),
        tool(
            "seo",
            "seo_calibrate",
            {
                "observations": [
                    {"predicted": 0.5, "actual": 0.45},
                    {"predicted": 0.2, "actual": 0.24},
                ]
            },
            digest=("slope", "intercept", "samples"),
        ),
        http("seo", "POST", "/seo/score", {"platform": "youtube", "pack": pack}),
        http(
            "seo",
            "POST",
            "/seo/optimize",
            {"platform": "youtube", "pack": pack},
            needs="provider",
        ),
        http("seo", "POST", "/seo/keywords", {"keywords": ["sóng thần"]}),
        http("seo", "POST", "/seo/ab/plan", {"baseline_rate": 0.04}),
        http("seo", "GET", "/seo/rules"),
    ]


def group_production(ctx: dict[str, Any]) -> list[Probe]:
    pid = ctx["project_id"]
    return [
        tool(
            "production",
            "start_generation",
            {"project_id": pid},
            expect=(200, 409),
            note="Already generating: 409 with a message is also correct",
            digest=("status", "stage", "steps"),
        ),
        tool(
            "production",
            "approve_stage",
            {"project_id": pid, "stage": "video", "verdict": "approved"},
            expect=(200, 409),
            note="Reviews the rendered cut so publish can follow",
            digest=("status", "stage"),
        ),
        tool(
            "production",
            "generate_voiceover",
            {"project_id": pid},
            needs="edge-tts+network",
            digest=("assets", "count", "voice"),
        ),
        tool(
            "production",
            "render_video",
            {"project_id": pid, "export_format": "mp4"},
            needs="ffmpeg",
            note="The slowest local path: full timeline render",
            digest=("asset_id", "url", "path", "duration"),
        ),
        tool(
            "production",
            "publish_project",
            {"project_id": pid, "platforms": ["youtube"]},
            digest=("status", "platforms", "published"),
        ),
        http("production", "POST", f"/projects/{pid}/render", {}),
        http(
            "production", "POST", f"/projects/{pid}/publish", {"platforms": ["youtube"]}
        ),
        http("production", "GET", f"/projects/{pid}/thumbnail"),
        http("production", "POST", f"/projects/{pid}/sensitivity/audit", {}),
        http(
            "production",
            "POST",
            "/cost/check",
            {
                "calls": {"anthropic": 2},
                "estimated_usage": {"input_tokens": 1000, "output_tokens": 500},
            },
            expect=(200, 422),
            note="Body shape read from the model; 422 means the schema disagrees",
        ),
        http("production", "GET", "/cost/estimate"),
        http(
            "production",
            "POST",
            "/audit/record",
            {"actor": "feature-audit", "action": "audit", "project_id": pid},
        ),
        http("production", "GET", "/audit"),
    ]


def group_network(ctx: dict[str, Any]) -> list[Probe]:
    return [
        tool(
            "network",
            "youtube_search",
            {"query": "sóng thần 2004 tư liệu", "limit": 3},
            needs="network",
            digest=("results", "count", "videos"),
        ),
        tool(
            "network",
            "kb_ingest_url",
            {
                "kb_id": "kb-missing",
                "url": "https://en.wikipedia.org/wiki/2004_Indian_Ocean_earthquake_and_tsunami",
            },
            expect=(400, 404),
            needs="network",
        ),
        tool(
            "network",
            "attach_kb",
            {"project_id": ctx["project_id"], "kb_id": ctx["kb_id"]},
            digest=("knowledge_base", "kb_id"),
        ),
        tool(
            "network",
            "ground_project",
            {"project_id": ctx["project_id"]},
            needs="network",
            digest=("sources", "count", "grounded"),
        ),
        tool(
            "network",
            "kb_ask",
            {"kb_id": ctx["kb_id"], "query": "Sóng thần cao bao nhiêu mét?"},
            needs="provider",
            digest=("answer", "chunks", "sources"),
        ),
        tool(
            "network",
            "kb_ingest_url",
            {
                "kb_id": ctx["kb_id"],
                "url": "https://en.wikipedia.org/wiki/2004_Indian_Ocean_earthquake_and_tsunami",
            },
            needs="network",
            digest=("document", "chunks", "title"),
        ),
        tool(
            "network",
            "kb_ask",
            {"kb_id": ctx["kb_id"], "query": "Khi nào xảy ra?"},
            needs="provider",
            digest=("answer", "chunks"),
        ),
        tool(
            "network",
            "research_project",
            {"project_id": ctx["project_id"], "include_web": False},
            needs="network",
            digest=("sources", "count"),
        ),
        tool(
            "network",
            "research_project",
            {"project_id": ctx["project_id"], "include_web": True},
            needs="network",
            digest=("sources", "count", "web"),
        ),
        tool(
            "network",
            "youtube_transcript",
            {"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
            needs="network+yt-dlp",
            digest=("language", "segments", "text"),
            expect=(200, 400, 404, 502, 503),
        ),
        http("network", "GET", "/documents/search?q=tsunami"),
        http("network", "GET", "/history/search?q=sóng thần"),
        http("network", "GET", "/history/on-this-day?month=12&day=26"),
        http("network", "GET", "/kb"),
        http(
            "network",
            "POST",
            "/kb",
            {
                "name": "Feature audit KB",
                "description": "created by scripts/feature_audit.py",
            },
        ),
    ]


def group_http(ctx: dict[str, Any]) -> list[Probe]:
    pid = ctx["project_id"]
    return [
        http("http", "GET", "/"),
        http("http", "GET", "/health"),
        http("http", "GET", "/tools"),
        http("http", "GET", "/projects"),
        http("http", "GET", f"/projects/{pid}"),
        http("http", "GET", f"/projects/{pid}/video-project"),
        http("http", "GET", f"/projects/{pid}/video"),
        http("http", "GET", f"/projects/{pid}/workflow"),
        http("http", "GET", f"/projects/{pid}/workflow/checklist"),
        http("http", "POST", f"/projects/{pid}/workflow/run", {"inputs": {}}),
        http("http", "GET", f"/projects/{pid}/research"),
        http("http", "GET", f"/projects/{pid}/campaign"),
        http("http", "POST", f"/projects/{pid}/campaign/generate", {}),
        http("http", "GET", f"/projects/{pid}/campaign/export-pack"),
        http(
            "http",
            "POST",
            f"/projects/{pid}/graphics/infographic",
            {
                "title": "Thiệt hại",
                "chart_type": "bar",
                "labels": ["A", "B", "C"],
                "values": [1, 4, 9],
            },
        ),
        http(
            "http",
            "POST",
            f"/projects/{pid}/graphics/map",
            {
                "title": "Tâm chấn",
                "markers": [{"lat": 3.3, "lon": 95.9, "label": "Sumatra"}],
            },
            expect=(200, 422),
        ),
        http(
            "http",
            "POST",
            f"/projects/{pid}/external/import",
            {
                "asset_type": "text",
                "raw_content": "Nội dung tham chiếu",
                "label": "ref",
            },
        ),
        http("http", "GET", f"/projects/{pid}/external/assets"),
        http(
            "http",
            "POST",
            f"/projects/{pid}/documents",
            {
                "id": "doc-1",
                "title": "2004 Indian Ocean tsunami",
                "year": 2005,
                "source": "audit",
            },
        ),
        http("http", "GET", f"/projects/{pid}/facts/reconcile", expect=(200, 405)),
        http("http", "POST", f"/projects/{pid}/facts/reconcile", {}),
        http("http", "GET", "/media"),
        http("http", "GET", "/media/stats"),
        http("http", "GET", "/media/tags"),
        http("http", "GET", f"/media/{ctx['media_id']}"),
        http("http", "POST", f"/media/{ctx['media_id']}/tags", {"tags": ["audit"]}),
        http(
            "http",
            "POST",
            f"/media/{ctx['media_id']}/transcribe",
            {},
            needs="faster-whisper",
            expect=(200, 202, 400, 422),
        ),
        http("http", "GET", "/media/search?q=audit"),
        http("http", "GET", "/library"),
        http("http", "GET", "/library/search?q=tsunami"),
        http("http", "GET", "/resources"),
        http("http", "GET", "/resources/kinds"),
        http("http", "GET", "/resources/explain"),
        http(
            "http",
            "POST",
            "/qa/brand",
            {"dominant_colors": ["#112233"], "fonts_used": ["Inter"], "has_logo": True},
        ),
        http(
            "http",
            "POST",
            "/qa/copyright",
            {"asset_ids": [ctx["media_id"]], "protected": []},
        ),
        http(
            "http",
            "POST",
            "/qa/platform",
            {
                "platform": "youtube",
                "duration_seconds": 45,
                "aspect_ratio": "9:16",
                "words": 120,
                "text": "Sóng thần 2004",
            },
        ),
        http(
            "http",
            "POST",
            "/subtitles/simplify",
            {
                "captions": [
                    {
                        "start": 0.0,
                        "end": 1.4,
                        "text": "Đại dương rút lui trước khi cơn sóng thần ập tới.",
                    }
                ],
                "level": "easy",
            },
        ),
        http("http", "GET", "/agents"),
        http("http", "GET", f"/projects/{pid}/approvals", expect=(200, 405)),
        http("http", "GET", "/does-not-exist", expect=(404,)),
        http(
            "http",
            "POST",
            "/tools/call",
            {"tool": "no_such_tool", "args": {}},
            expect=(422,),
        ),
        http("http", "POST", "/projects", {"name": "", "topic": ""}, expect=(422,)),
    ]


def group_negative(ctx: dict[str, Any]) -> list[Probe]:
    """Invalid input must answer 4xx with a message, never 500 with nothing."""
    voice = ctx["voice_b64"]
    chart = ctx["chart_b64"]
    bad_audio = b64_of(b"definitely not audio")
    bad_image = b64_of(b"definitely not an image")
    cases: list[tuple[str, str, dict[str, Any]]] = [  # (label, tool, args)
        (
            "unknown image op",
            "edit_image",
            {"image_b64": chart, "ops": [{"name": "magic"}]},
        ),
        ("garbage image bytes", "edit_image", {"image_b64": bad_image, "ops": []}),
        (
            "unknown audio effect",
            "apply_audio_effect",
            {"audio_b64": voice, "name": "normalise"},
        ),
        (
            "garbage audio bytes",
            "apply_audio_effect",
            {"audio_b64": bad_audio, "name": "telephone"},
        ),
        (
            "bad audio format",
            "apply_audio_effect",
            {"audio_b64": voice, "name": "telephone", "format": "flac"},
        ),
        (
            "unknown video effect",
            "apply_video_effect",
            {"image_b64": chart, "name": "vhs"},
        ),
        ("unknown sfx name", "synthesize_sfx", {"name": "laser"}),
        ("garbage audio analysis", "analyze_audio", {"audio_b64": bad_audio}),
        ("garbage audio description", "describe_audio", {"audio_b64": bad_audio}),
        (
            "out-of-range stem count",
            "separate_audio_stems",
            {"audio_b64": voice, "num": 9},
        ),
        (
            "unknown voice preset",
            "enhance_voice",
            {"audio_b64": voice, "preset": "nope"},
        ),
        (
            "unknown session id (edit)",
            "edit_image_session",
            {"session_id": "nope", "ops": []},
        ),
        ("unknown session id (undo)", "undo_image_session", {"session_id": "nope"}),
        ("garbage mastering input", "apply_audio_mastering", {"audio_b64": bad_audio}),
        (
            "dub without an adapter",
            "dub_audio",
            {"audio_b64": voice, "target_text": "hello", "lang": "vi"},
        ),
        (
            "clone without an adapter",
            "voice_clone",
            {"audio_b64": voice, "ref_voice": voice},
        ),
        ("missing required arg", "seo_score", {}),
        ("bad ref", "inspect_media", {"ref": "no/such/file.mp4"}),
    ]
    # A missing *capability* is not a malformed request: ``dub_audio`` and
    # ``voice_clone`` have no ML adapter installed, so 503 ("not available") with
    # the message naming the adapter is the honest answer, and the point of the
    # case is that the client *sees* that message instead of an empty 500.
    unavailable = {"dub_audio", "voice_clone"}
    return [
        tool(
            "negative",
            target,
            args,
            label=f"{label} [{target}]",
            expect=(400, 404, 409, 415, 422, 503)
            if target in unavailable
            else (400, 404, 409, 415, 422),
            note="a 4xx/503 with a message is the correct answer here",
        )
        for label, target, args in cases
    ]


GROUPS: dict[str, Callable[[dict[str, Any]], list[Probe]]] = {
    "vision": group_vision,
    "catalog": group_catalog,
    "image": group_image,
    "audio": group_audio,
    "media": group_media,
    "timeline": group_timeline,
    "script": group_script,
    "seo": group_seo,
    "production": group_production,
    "network": group_network,
    "http": group_http,
    "negative": group_negative,
}

GROUP_ORDER = list(GROUPS)


# --------------------------------------------------------------------------- #
# session setup
# --------------------------------------------------------------------------- #


def wait_healthy(timeout: float) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            status, _, _ = _request("GET", "/health", None, 2.0)
            if status == 200:
                return
        except OSError:
            pass
        time.sleep(0.4)
    raise RuntimeError(f"no healthy server on {BASE}")


def post(
    path: str, body: dict[str, Any] | None = None, expect: tuple[int, ...] = (200, 201)
) -> dict[str, Any]:
    """POST a fixture and return the body; raises unless the status is expected."""
    status, raw, seconds = _request("POST", path, body, 300.0)
    if status not in expect:
        raise RuntimeError(f"POST {path} -> HTTP {status}: {raw[:300]!r}")
    print(f"  [[setup]] POST {path} {seconds:.2f}s")
    return json.loads(raw.decode("utf-8"))


def call_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    return post("/tools/call", {"tool": name, "args": args})


def _decodable_images(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep only library images Pillow can actually open.

    The shared ``library/`` carries test leftovers (a 108-byte ``pic.png``),
    and a tool handed one answers 500 — so pick a real image for the happy path.
    """
    from PIL import Image

    healthy: list[dict[str, Any]] = []
    for item in items:
        path = (
            ROOT
            / "library"
            / "media"
            / "files"
            / f"{item['id']}_{item.get('filename', '')}"
        )
        if not path.is_file():
            continue
        try:
            Image.open(path).verify()
        except Exception:  # noqa: BLE001 - an unreadable fixture is a finding, not an error
            continue
        healthy.append(item)
    return healthy


def as_items(body: Any) -> list[dict[str, Any]]:
    """Normalise ``list_media`` and friends, which return a list *or* an envelope."""
    if isinstance(body, list):
        return [item for item in body if isinstance(item, dict)]
    if isinstance(body, dict):
        for key in ("items", "media", "results", "assets", "entries"):
            value = body.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def find_key(body: Any, key: str) -> Any:
    """First ``key`` anywhere in a nested response, so chains survive nesting."""
    if isinstance(body, dict):
        if key in body:
            return body[key]
        for value in body.values():
            found = find_key(value, key)
            if found is not None:
                return found
    elif isinstance(body, list):
        for value in body:
            found = find_key(value, key)
            if found is not None:
                return found
    return None


def build_context() -> dict[str, Any]:
    """Create every fixture the probe groups need."""
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    chart = synthetic_png()
    shot = audit_screenshot()
    voice = speech_like_wav()
    music_bytes = speech_like_wav(4.0)
    clip = make_mp4(FIXTURE_DIR / "audit_clip.mp4")
    ctx: dict[str, Any] = {
        "chart_b64": b64_of(chart),
        "shot_b64": b64_of(shot),
        "shot_bytes": shot,
        "voice_b64": b64_of(voice),
        "music_b64": b64_of(music_bytes),
        "chart_bytes": chart,
        "voice_bytes": voice,
        "chart_png": FIXTURE_DIR / "chart.png",
        "clip_path": clip,
        # A real video with a *video* stream (the library holds audio-only clips
        # filed as videos, which is itself an audit finding).
        "local_video_ref": clip.relative_to(ROOT).as_posix(),
    }
    ctx["chart_png"].write_bytes(chart)

    ctx["project_id"] = post(
        "/projects",
        {
            "name": "Feature audit",
            "topic": "Sóng thần Ấn Độ Dương 2004",
            "target_language": "vi",
            "duration_target_seconds": 45,
        },
    )["id"]
    script = (
        "[Hook]\nĐại dương rút lui trước khi cơn sóng thần ập tới.\n\n"
        "[Turn]\nKhông ai trên bãi biển hiểu điều gì đang tới.\n\n"
        "[Outro]\nBa đại dương gợn sóng trong cùng một ngày."
    )
    call_tool(
        "update_script",
        {
            "project_id": ctx["project_id"],
            "script": script,
            "source_rights_confirmed": True,
        },
    )
    call_tool(
        "approve_stage",
        {"project_id": ctx["project_id"], "stage": "script", "verdict": "approved"},
    )
    built = call_tool("build_video_project", {"project_id": ctx["project_id"]})
    scenes = (built.get("video_project") or {}).get("scenes") or []
    if not scenes:
        raise RuntimeError(f"build_video_project produced no scenes: {built}")
    ctx["project_body"] = call_tool("get_project", {"project_id": ctx["project_id"]})
    ctx["scene_id"] = scenes[0]["id"]
    ctx["scene_id_2"] = scenes[1]["id"] if len(scenes) > 1 else scenes[0]["id"]
    # Timeline edits and the vision/AI helpers only work once generation has
    # started (the same ordering scripts/smoke.py uses).
    call_tool("start_generation", {"project_id": ctx["project_id"]})

    items = as_items(call_tool("list_media", {}))
    videos = [i for i in items if str(i.get("kind")) == "video"]
    images = _decodable_images([i for i in items if str(i.get("kind")) == "image"])
    if videos:
        ctx["media_id"] = videos[0]["id"]
        ctx["video_ref"] = videos[0]["id"]
    if len(images) >= 2:
        ctx["image_ref"] = images[0]["id"]
        ctx["image_ref_2"] = images[1]["id"]
    if not ctx.get("video_ref") or not ctx.get("image_ref"):
        kinds = sorted({str(i.get("kind")) for i in items})
        raise RuntimeError(f"library lacks video/image fixtures: kinds={kinds}")

    # A real music file for beat/ducking probes.
    music_dir = ROOT / "library" / "music"
    music_files = sorted(music_dir.glob("*.ogg")) or sorted(music_dir.glob("*.mp3"))
    if not music_files:
        raise RuntimeError("no music fixture in library/music")
    ctx["music_ref"] = str(music_files[0].relative_to(ROOT))

    # Edited assets produced by the media probes, referenced by later groups.
    ctx["edited_audio_ref"] = ""
    return ctx


def prepare_dependencies(ctx: dict[str, Any], groups: list[str]) -> None:
    """Produce the assets some groups chain off (trim needs an audio asset...)."""
    produced = call_tool(
        "apply_audio_effect",
        {
            "audio_b64": ctx["voice_b64"],
            "name": "telephone",
            "params": {},
            "format": "wav",
        },
    )
    ctx["edited_audio_ref"] = (
        find_key(produced, "asset_id") or find_key(produced, "url") or ""
    )
    first = call_tool(
        "cut_media",
        {"ref": ctx["local_video_ref"], "start_seconds": 0.0, "end_seconds": 1.2},
    )
    ctx["clip_a_ref"] = find_key(first, "asset_id") or find_key(first, "url")
    second = call_tool(
        "cut_media",
        {"ref": ctx["local_video_ref"], "start_seconds": 2.0, "end_seconds": 3.2},
    )
    ctx["clip_b_ref"] = find_key(second, "asset_id") or find_key(second, "url")
    if not (ctx["edited_audio_ref"] and ctx["clip_a_ref"] and ctx["clip_b_ref"]):
        raise RuntimeError(
            "fixture assets missing: "
            f"{ctx['edited_audio_ref']!r} {ctx['clip_a_ref']!r} {ctx['clip_b_ref']!r}"
        )
    kb = post(
        "/kb",
        {
            "name": "Feature audit KB",
            "description": "created by scripts/feature_audit.py",
        },
    )
    ctx["kb_id"] = find_key(kb, "id") or find_key(kb, "kb_id")


def refresh_scenes(ctx: dict[str, Any]) -> None:
    """Re-read the scene ids the pipeline currently has.

    The background generation job rebuilds the video project as it advances, so
    ids captured at build time are stale by the time an agent edits them.
    """
    body = call_tool("get_project", {"project_id": ctx["project_id"]})
    scenes = (body.get("video_project") or {}).get("scenes") or []
    ctx["project_body"] = body
    if scenes:
        before = ctx.get("scene_id")
        ctx["scene_id"] = scenes[0]["id"]
        ctx["scene_id_2"] = scenes[1]["id"] if len(scenes) > 1 else scenes[0]["id"]
        moved = " (ids changed since build)" if before != ctx["scene_id"] else ""
        print(f"  [[scenes]] {[s['id'][:6] for s in scenes]}{moved}")


def settle_pipeline(project_id: str, timeout: float = 90.0) -> str:
    """Wait for the background generation job to stop changing the project.

    Rendering an un-settled project is rejected with 409 ("project changed
    during rendering"), so the audit settles it first and records the states it
    passed through.
    """
    last = ""
    stable = 0
    deadline = time.time() + timeout
    while time.time() < deadline:
        _, raw, _ = _request(
            "POST",
            "/tools/call",
            {"tool": "get_project", "args": {"project_id": project_id}},
            30.0,
        )
        status = json.loads(raw.decode("utf-8")).get("status", "?")
        stable = stable + 1 if status == last else 0
        last = status
        print(f"  [[settle]] status={status}")
        if stable >= 1:
            return status
        time.sleep(1.0)
    return last


def fill_session_probes(
    ctx: dict[str, Any], probes: list[Probe], session_id: str
) -> None:
    """The image-session chain needs the id returned by ``begin_image_session``."""
    for probe in probes:
        name = probe.name.removeprefix("tool:")
        args: dict[str, Any] = {}
        if name == "edit_image_session":
            args = {
                "session_id": session_id,
                "ops": [{"name": "filter", "params": {"preset": "warm"}}],
                "format": "png",
            }
            probe.digest = ("session_id", "ops", "width", "height")
            probe.note = "Apply an op inside the session"
        elif name == "undo_image_session":
            args = {"session_id": session_id}
            probe.note = "Undo the session op"
        elif name == "redo_image_session":
            args = {"session_id": session_id}
            probe.note = "Redo it"
        elif name == "image_session_state":
            args = {"session_id": session_id}
            probe.digest = ("session_id", "ops", "can_undo", "can_redo")
            probe.note = "Session state after edit/undo/redo"
        probe.payload = {"tool": name, "args": args}


# --------------------------------------------------------------------------- #
# reporting
# --------------------------------------------------------------------------- #


def write_markdown(path: Path, records: list[dict[str, Any]], started: float) -> None:
    by_group: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        by_group.setdefault(record["group"], []).append(record)
    lines = [
        "# Feature audit — measured run",
        "",
        "Generated by `python scripts/feature_audit.py` "
        f"({time.strftime('%Y-%m-%d %H:%M')}, "
        f"wall clock {time.perf_counter() - started:.0f}s).",
        "Every row is one real call over HTTP; `needs` names the dependency the",
        "feature requires beyond the standard library.",
        "",
        "## Summary",
        "",
        "| Group | Calls | Pass | Fail | Seconds |",
        "| :--- | ---: | ---: | ---: | ---: |",
    ]
    for group in GROUP_ORDER:
        rows = by_group.get(group)
        if not rows:
            continue
        passed = sum(1 for r in rows if r["outcome"] == "pass")
        lines.append(
            f"| {group} | {len(rows)} | {passed} | {len(rows) - passed} | "
            f"{sum(r['seconds'] for r in rows):.1f} |"
        )
    total = len(records)
    passed = sum(1 for r in records if r["outcome"] == "pass")
    lines += [
        f"| **total** | **{total}** | **{passed}** | **{total - passed}** | "
        f"**{sum(r['seconds'] for r in records):.1f}** |",
        "",
    ]
    for group in GROUP_ORDER:
        rows = by_group.get(group)
        if not rows:
            continue
        lines += [
            f"## {group}",
            "",
            "| Call | needs | HTTP | seconds | result |",
            "| :--- | :--- | ---: | ---: | :--- |",
        ]
        for record in rows:
            detail = str(record.get("detail", "")).replace("|", "/")
            lines.append(
                f"| `{record['name']}` | {record['needs']} | {record['status']} | "
                f"{record['seconds']:.3f} | {detail} |"
            )
        lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nwrote {path}")


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--port", type=int, default=int(os.environ.get("AUDIT_PORT", "8188"))
    )
    parser.add_argument(
        "--groups",
        default=",".join(GROUP_ORDER),
        help=f"subset of {','.join(GROUP_ORDER)}",
    )
    parser.add_argument(
        "--json", type=Path, default=None, help="write the raw record log here"
    )
    parser.add_argument(
        "--md", type=Path, default=None, help="write a markdown report here"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    global BASE
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = parse_args(argv)
    BASE = f"http://127.0.0.1:{args.port}"
    groups = [g.strip() for g in args.groups.split(",") if g.strip()]
    unknown = [g for g in groups if g not in GROUPS]
    if unknown:
        print(f"unknown groups: {unknown}; known: {GROUP_ORDER}")
        return 2

    spawned: subprocess.Popen | None = None
    try:
        wait_healthy(3.0)
        print(f"[reuse] server already listening on {BASE}")
    except RuntimeError:
        log_path = ROOT / "storage" / "feature-audit-server.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log = log_path.open("w", encoding="utf-8", errors="replace")
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
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        print(f"[log] server stderr -> {log_path.relative_to(ROOT)}")
        wait_healthy(45.0)
        print(f"[spawn] fresh server on {BASE}")

    started = time.perf_counter()
    try:
        print("\n== fixtures ==")
        ctx = build_context()
        prepare_dependencies(ctx, groups)
        print(f"  project={ctx['project_id']} scene={ctx['scene_id']}")
        print(f"  video={ctx['video_ref']} image={ctx['image_ref']}")
        print(f"  music={ctx['music_ref']} kb={ctx.get('kb_id')}")

        for group in groups:
            print(f"\n== {group} ==")
            if group in {"timeline", "script", "seo"}:
                refresh_scenes(ctx)
            if group == "production":
                settle_pipeline(ctx["project_id"])
            probes = GROUPS[group](ctx)
            session_probe = next(
                (p for p in probes if p.name == "tool:begin_image_session"), None
            )
            for probe in probes:
                if probe.name in {
                    "tool:edit_image_session",
                    "tool:undo_image_session",
                    "tool:redo_image_session",
                    "tool:image_session_state",
                }:
                    session_id = ""
                    if session_probe and isinstance(session_probe.result, dict):
                        session_id = str(session_probe.result.get("session_id", ""))
                    fill_session_probes(ctx, [probe], session_id)
                record = run_probe(probe)
                if (
                    probe.name == "tool:build_video_project"
                    and record["outcome"] == "pass"
                ):
                    scenes = (probe.result.get("video_project") or {}).get(
                        "scenes"
                    ) or []
                    if scenes:
                        ctx["scene_id"] = scenes[0]["id"]
                        ctx["scene_id_2"] = (
                            scenes[1]["id"] if len(scenes) > 1 else scenes[0]["id"]
                        )
    finally:
        if spawned is not None:
            spawned.terminate()
            try:
                spawned.wait(timeout=10)
            except subprocess.TimeoutExpired:
                spawned.kill()

    passed = sum(1 for r in RECORDS if r["outcome"] == "pass")
    print("-" * 62)
    print(f"{passed}/{len(RECORDS)} calls returned the expected status")
    for record in RECORDS:
        if record["outcome"] != "pass":
            print(
                f"  FAIL {record['name']} (HTTP {record['status']}): {record['detail']}"
            )
    if args.json:
        args.json.write_text(json.dumps(RECORDS, indent=2), encoding="utf-8")
        print(f"wrote {args.json}")
    if args.md:
        write_markdown(args.md, RECORDS, started)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
