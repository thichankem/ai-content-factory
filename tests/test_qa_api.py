"""API tests for the QA, traceability, media-intelligence and booster endpoints."""

from __future__ import annotations

import wave

import numpy as np
from fastapi.testclient import TestClient

from content_factory.api import create_app
from content_factory.config import Settings


def _png_bytes(width: int = 8, height: int = 8, value: int = 200) -> bytes:
    """A tiny solid-color PNG."""
    from io import BytesIO

    from PIL import Image

    buf = BytesIO()
    Image.new("RGB", (width, height), (value, value, value)).save(buf, format="PNG")
    return buf.getvalue()


def _wav_bytes(duration: float = 0.5, amp: float = 0.5, rate: int = 8000) -> bytes:
    """A tiny mono WAV (a steady tone)."""
    samples = amp * np.sin(2 * np.pi * 440 * np.arange(int(rate * duration)) / rate)
    pcm = (np.clip(samples, -1, 1) * 32767).astype(np.int16)
    buf = __import__("io").BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(pcm.tobytes())
    return buf.getvalue()


def _upload(client: TestClient, filename: str, content: bytes) -> str:
    resp = client.post(
        "/media/upload",
        files={"file": (filename, content, "application/octet-stream")},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_qa_platform_flags_too_long_tiktok(client) -> None:
    resp = client.post(
        "/qa/platform",
        json={
            "platform": "tiktok",
            "duration_seconds": 1200,
            "aspect_ratio": "9:16",
        },
    )
    assert resp.status_code == 200
    codes = {issue["code"] for issue in resp.json()}
    assert "duration_too_long" in codes


def test_qa_platform_ok_for_compliant_youtube(client) -> None:
    resp = client.post(
        "/qa/platform",
        json={
            "platform": "youtube",
            "duration_seconds": 300,
            "aspect_ratio": "16:9",
            "words": 500,
        },
    )
    assert resp.status_code == 200
    assert resp.json() == []


def test_qa_brand_flags_missing_logo(client) -> None:
    resp = client.post(
        "/qa/brand",
        json={
            "dominant_colors": ["#1a1d27"],
            "fonts_used": ["Inter"],
            "has_logo": False,
            "palette": ["#1a1d27"],
            "fonts": ["Inter"],
        },
    )
    assert resp.status_code == 200
    codes = {issue["code"] for issue in resp.json()}
    assert "missing_logo" in codes


def test_qa_copyright_flags_exact_match(client) -> None:
    resp = client.post(
        "/qa/copyright", json={"fingerprint": "abc123", "protected": ["abc123"]}
    )
    assert resp.status_code == 200
    assert resp.json()[0]["code"] == "copyright_match"


def test_audit_record_and_list(tmp_path) -> None:
    settings = Settings(
        template_enabled=False,
        money_printer_enabled=False,
        strong_llm_enabled=False,
        audit_dir=str(tmp_path / "audit"),
    )
    client = TestClient(create_app(settings))
    resp = client.post(
        "/audit/record",
        json={"actor": "claude", "action": "edit.scene.speed", "project_id": "p1"},
    )
    assert resp.status_code == 200
    listed = client.get("/audit").json()
    assert any(entry["actor"] == "claude" for entry in listed)


def test_cost_check_estimates_and_confirms(client) -> None:
    settings = Settings(
        template_enabled=False,
        money_printer_enabled=False,
        strong_llm_enabled=False,
        cost_guard_enabled=True,
        cost_guard_threshold_usd=1.0,
    )
    client = TestClient(create_app(settings))
    resp = client.post("/cost/check", json={"calls": {"vision": 200, "tts": 5}})
    assert resp.status_code == 200
    body = resp.json()
    assert body["estimate_usd"] > 1.0
    assert body["needs_confirmation"] is True


def test_media_dedup_groups_identical_images(client) -> None:
    a = _upload(client, "a.png", _png_bytes())
    b = _upload(client, "b.png", _png_bytes())
    resp = client.post("/media/dedup", json={"media_ids": [a, b]})
    assert resp.status_code == 200
    body = resp.json()
    assert any({a, b}.issubset(set(group)) for group in body["groups"])
    assert body["count"] == 1
    assert body["checked"] == 2
    pair = body["duplicates"][0]
    assert {pair["original"], pair["duplicate"]} == {a, b}
    assert pair["similarity"] == 1.0


def test_media_dedup_without_a_body_sweeps_the_library(client) -> None:
    """One-click cleanup posts nothing and still gets an answer.

    The studio has no ids to hand over, so an absent body must mean "check
    everything" instead of a 422 that leaves the button dead.
    """
    a = _upload(client, "a.png", _png_bytes())
    b = _upload(client, "b.png", _png_bytes())
    resp = client.post("/media/dedup")
    assert resp.status_code == 200
    body = resp.json()
    assert body["checked"] >= 2
    assert any({a, b}.issubset(set(group)) for group in body["groups"])


def test_media_search_finds_distinctive_document(client) -> None:
    media_id = _upload(
        client, "note.txt", b"The aurora borealis glows over the fjord tonight."
    )
    resp = client.get("/media/search", params={"q": "aurora fjord"})
    assert resp.status_code == 200
    hits = resp.json()
    assert hits and hits[0]["media_id"] == media_id


def test_script_virality_returns_score_and_warnings(client) -> None:
    resp = client.post(
        "/script/virality",
        json={
            "script": "You won't believe what happens next. Watch this.",
            "duration_seconds": 45,
            "hook": "You won't believe this",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert 0 <= body["score"] <= 100
    assert isinstance(body["warnings"], list)


def test_render_duck_produces_output(client) -> None:
    music = _upload(client, "music.wav", _wav_bytes())
    voice = _upload(client, "voice.wav", _wav_bytes(amp=0.9))
    resp = client.post(
        "/render/duck", json={"music_media_id": music, "voice_media_id": voice}
    )
    assert resp.status_code == 200
    assert resp.json()["out"]


def test_thumbnail_generate_returns_candidates(client) -> None:
    # Build a tiny avi via cv2 and upload it.
    import tempfile
    from pathlib import Path

    import cv2

    tmp = Path(tempfile.gettempdir()) / "cf-thumb-test.avi"
    writer = cv2.VideoWriter(str(tmp), cv2.VideoWriter_fourcc(*"MJPG"), 15, (160, 90))
    for _ in range(30):
        writer.write(np.full((90, 160, 3), 120, dtype=np.uint8))
    writer.release()
    media_id = _upload(client, "clip.avi", tmp.read_bytes())
    tmp.unlink(missing_ok=True)

    resp = client.post(
        "/thumbnail/generate",
        json={"media_id": media_id, "top_k": 2, "overlays": ["Watch till the end"]},
    )
    assert resp.status_code == 200
    candidates = resp.json()
    assert len(candidates) == 2
    assert candidates[0]["ctr_prediction"] >= candidates[1]["ctr_prediction"]


def test_qa_router_404_on_missing_media(client) -> None:
    resp = client.post(
        "/render/duck", json={"music_media_id": "nope", "voice_media_id": "nope"}
    )
    assert resp.status_code == 404


def test_timeline_command_applies_speed(client) -> None:
    project = {
        "scenes": [
            {
                "id": "s1",
                "label": "Intro",
                "text": "You won't believe this.",
                "duration_seconds": 4.0,
            },
            {
                "id": "s2",
                "label": "Outro",
                "text": "Follow for more.",
                "duration_seconds": 3.0,
            },
        ]
    }
    resp = client.post(
        "/timeline/command",
        json={"project": project, "text": "speed up the intro to 1.5x"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["command"]["intent"] == "speed_up"
    assert body["project"]["scenes"][0]["speed"] == 1.5


def test_subtitles_simplify(client) -> None:
    resp = client.post(
        "/subtitles/simplify",
        json={
            "captions": ["The individual attempted to purchase a vehicle."],
            "level": "basic",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["level"] == "basic"
    assert body["captions"][0]["simplified"] == "The person tried to buy a car."
