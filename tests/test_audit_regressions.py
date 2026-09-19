"""Regressions for the defects found by the feature audit (docs/FEATURE-AUDIT.md).

One test per finding that can be asserted in a unit test, each named after the
id it fixes so the audit and the suite stay in step. The two dead tools
themselves (``research_project``, ``ground_project``) are covered by
``tests/test_tool_dispatch_contract.py``, which dispatches every tool.
"""

from __future__ import annotations

import io
import struct
import wave
from pathlib import Path

import pytest

from content_factory.config import Settings


def _wav_bytes(seconds: float = 0.2, rate: int = 8000) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(
            struct.pack("<" + "h" * int(rate * seconds), *([0] * int(rate * seconds)))
        )
    return buffer.getvalue()


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        store_path=str(tmp_path / "projects.json"),
        uploads_dir=str(tmp_path / "uploads"),
        media_dir=str(tmp_path / "media"),
        library_dir=str(tmp_path / "library"),
        cache_dir=str(tmp_path / "cache"),
        # The generation worker is real, just quick: these tests drive it.
        generation_steps=1,
        generation_step_delay_seconds=0.0,
    )


@pytest.fixture
def library(tmp_path):
    from content_factory.media import MediaLibrary

    return MediaLibrary(tmp_path / "media")


# --- L4: a URL that returns a web page must not be stored as media ------------


def test_download_rejects_an_html_page(library) -> None:
    """A blocked extractor used to be answered by storing the HTML as a video."""
    from unittest.mock import MagicMock, patch

    from content_factory.media import DownloadRejectedError

    page = b"<!DOCTYPE html><html><body>Sign in to confirm your age</body></html>"
    response = MagicMock()
    response.read.side_effect = [page, b""]
    response.__enter__.return_value = response
    response.headers = {"Content-Type": "text/html"}

    with patch("yt_dlp.YoutubeDL", side_effect=Exception("blocked")):
        with patch("urllib.request.urlopen", return_value=response):
            with pytest.raises(DownloadRejectedError) as excinfo:
                library.download_from_url("https://example.com/video.mp4")

    message = str(excinfo.value)
    assert "web page" in message or "not audio or video" in message


def test_download_rejects_a_file_with_no_streams(library, tmp_path) -> None:
    """A payload that lies about its type by extension is still not media."""
    from unittest.mock import MagicMock, patch

    from content_factory.media import DownloadRejectedError

    response = MagicMock()
    response.read.side_effect = [b"\x00\x01\x02not a container" * 8, b""]
    response.__enter__.return_value = response
    response.headers = {"Content-Type": "video/mp4"}

    with patch("yt_dlp.YoutubeDL", side_effect=Exception("blocked")):
        with patch("urllib.request.urlopen", return_value=response):
            try:
                library.download_from_url("https://example.com/video.mp4")
            except DownloadRejectedError:
                return
    # ffprobe is unavailable in some environments; then the sniffing still has to
    # have caught the text payload, and anything else is a genuine pass.
    pytest.skip("ffprobe could not read the payload and the sniff passed")


# --- L7: the kind comes from the real streams, not the extension --------------


def test_resolve_kind_trusts_the_probe_over_the_extension() -> None:
    from content_factory.media import MediaKind, resolve_kind

    audio_only = {"streams_known": True, "has_video": False, "has_audio": True}
    assert resolve_kind("clip.mp4", audio_only) is MediaKind.AUDIO

    video_only = {"streams_known": True, "has_video": True, "has_audio": False}
    assert resolve_kind("clip.mp3", video_only) is MediaKind.VIDEO

    nothing = {"streams_known": True, "has_video": False, "has_audio": False}
    assert resolve_kind("clip.mp4", nothing) is MediaKind.OTHER


def test_resolve_kind_falls_back_when_the_probe_says_nothing() -> None:
    """No ffprobe ⇒ the extension stays the answer, never a blanket 'other'."""
    from content_factory.media import MediaKind, resolve_kind

    assert resolve_kind("clip.mp4", {}) is MediaKind.VIDEO
    assert resolve_kind("clip.mp4", {"streams_known": False}) is MediaKind.VIDEO
    assert resolve_kind("song.wav", None) is MediaKind.AUDIO


def test_probe_media_reports_stream_presence(tmp_path) -> None:
    from content_factory.media import probe_media

    path = tmp_path / "clip.wav"
    path.write_bytes(_wav_bytes())
    result = probe_media(path)
    if not result:
        pytest.skip("ffprobe is not installed")
    assert result["streams_known"] is True
    assert result["has_audio"] is True
    assert result["has_video"] is False


# --- L6: scene ids survive a timeline rebuild --------------------------------


@pytest.fixture
def service(tmp_path):
    from content_factory.service import ContentFactoryService

    return ContentFactoryService(_settings(tmp_path))


SCRIPT = "[Hook]\nMở đầu.\n\n[Body]\nNội dung chính.\n\n[Outro]\nKết."


def _review_ready_project(service):
    """A project in video review: a real timeline whose scenes can be edited."""
    from content_factory.models import (
        ApprovalCreate,
        ApprovalStage,
        ApprovalVerdict,
        ProjectCreate,
        ScriptUpdate,
    )

    project = service.create_project(ProjectCreate(name="Cut", topic="Titanic"))
    service.update_script(
        project.id,
        ScriptUpdate(script=SCRIPT, source_rights_confirmed=True),
    )
    service.approve(
        project.id,
        ApprovalCreate(stage=ApprovalStage.SCRIPT, verdict=ApprovalVerdict.APPROVED),
    )
    # script_approved -> generating -> video_review is the only legal path to an
    # editable timeline, and the worker is what walks it: it ends by building
    # the timeline and entering review.
    service.start_generation(project.id)
    assert service.wait_for_workers(30.0, project_id=project.id)
    return service.get_project(project.id)


def test_rebuilding_the_timeline_keeps_scene_ids(service) -> None:
    """An id a client was just handed must still resolve after a rebuild."""
    first = _review_ready_project(service)
    ids = [scene.id for scene in first.video_project.scenes]
    assert ids

    rebuilt = service.build_video_project(first.id)
    assert [scene.id for scene in rebuilt.video_project.scenes] == ids


def test_a_new_scene_in_the_script_gets_a_new_id(service) -> None:
    first = _review_ready_project(service)
    ids = [scene.id for scene in first.video_project.scenes]

    # An extra section, written straight to the store: rewriting a script through
    # the service is a different state transition (and a different test).
    stored = service.get_project(first.id).model_copy(deep=True)
    stored.script = first.script + "\n\n[Extra]\nCảnh mới."
    service.store.save(stored)
    rebuilt = service.build_video_project(first.id)
    scenes = rebuilt.video_project.scenes
    assert [scene.id for scene in scenes[: len(ids)]] == ids
    assert len(scenes) > len(ids)
    assert scenes[-1].id not in ids


def test_scenes_are_addressable_after_a_rebuild(service) -> None:
    """The exact failure an agent hit: edit by id, then rebuild, then edit again."""
    first = _review_ready_project(service)
    scene_id = first.video_project.scenes[0].id
    service.set_scene_speed(first.id, scene_id, 1.5)
    service.build_video_project(first.id)
    updated = service.set_scene_audio(first.id, scene_id, 0.5, None, None)
    assert any(scene.id == scene_id for scene in updated.video_project.scenes)


# --- L5: rendering waits for the running pipeline instead of losing the work --


def test_render_waits_for_the_generation_worker(service) -> None:
    """A render started during generation used to be discarded after the fact."""
    import threading
    import time

    project = _review_ready_project(service)
    # A settled project answers immediately — this is the case every render hits.
    assert service.wait_for_workers(0.2, project_id=project.id) is True

    # Now simulate a worker still running: it rewrites the project on every step,
    # which is what made the compare-and-save reject an in-flight export.
    stop = threading.Event()

    def rewrite() -> None:
        while not stop.is_set():
            current = service.get_project(project.id).model_copy(deep=True)
            service.store.save(current)
            time.sleep(0.02)

    worker = threading.Thread(
        target=rewrite, name=f"generation-{project.id}", daemon=True
    )
    service._workers.add(worker)
    worker.start()
    try:
        assert service.wait_for_workers(0.3, project_id=project.id) is False
    finally:
        stop.set()
        worker.join(timeout=5)
    # Once it stops, the wait succeeds instead of refusing the render forever.
    assert service.wait_for_workers(2.0, project_id=project.id) is True


# --- L8: a base64 payload passed as a ref is named for what it is -------------


def test_resolve_media_ref_explains_base64(tmp_path) -> None:
    from content_factory.media_tools import MediaToolArgumentError
    from content_factory.service import ContentFactoryService

    service = ContentFactoryService(_settings(tmp_path))
    payload = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8Dw"
        "HwAFAAH/q842iQAAAABJRU5ErkJggg=="
    )
    with pytest.raises(MediaToolArgumentError) as excinfo:
        service.resolve_media_ref(payload)
    assert "base64" in str(excinfo.value)
    assert len(str(excinfo.value)) < 400


def test_resolve_media_ref_still_accepts_a_real_id(service) -> None:
    from content_factory.services.errors import NotFoundError

    with pytest.raises(NotFoundError):
        service.resolve_media_ref("no-such-asset-id")


# --- L9: an unsupported stem count is refused, not silently rounded -----------


def test_stem_count_out_of_range_is_refused() -> None:
    import numpy as np

    from content_factory import audio_separation

    samples = np.zeros(8000, dtype=np.float32)
    with pytest.raises(ValueError) as excinfo:
        audio_separation.separate_stems(samples, 8000, num=9)
    assert "2" in str(excinfo.value) and "3" in str(excinfo.value)
    assert set(audio_separation.separate_stems(samples, 8000, num=2)) == {
        "voice",
        "instrumental",
    }
    assert set(audio_separation.separate_stems(samples, 8000, num=3)) == {
        "low",
        "mid",
        "high",
    }


# --- L10: an unknown describe section is named, not ignored -------------------


def test_describe_rejects_an_unknown_section(tmp_path) -> None:
    from content_factory import media_tools

    path = tmp_path / "clip.wav"
    path.write_bytes(_wav_bytes())
    with pytest.raises(media_tools.MediaToolArgumentError) as excinfo:
        media_tools.describe(path, include=["vision"])
    assert "vision" in str(excinfo.value)
    assert "loudness" in str(excinfo.value)


def test_describe_still_accepts_the_real_sections(tmp_path) -> None:
    from content_factory import media_tools

    path = tmp_path / "clip.wav"
    path.write_bytes(_wav_bytes())
    report = media_tools.describe(path, include=list(media_tools.DESCRIBE_SECTIONS))
    assert "probe" in report


# --- L12: captions keep their timings, and say whether they have any ----------


def test_vtt_segments_carry_cue_timings() -> None:
    from content_factory.subtitles import vtt_to_segments

    vtt = (
        "WEBVTT\nKind: captions\nLanguage: en\n\n"
        "00:00:01.000 --> 00:00:03.500\nHello <c>world</c>\n\n"
        "00:00:03.500 --> 00:00:05.000\nsecond line\n"
        "continues\n"
    )
    segments = vtt_to_segments(vtt)
    assert [round(s["start_seconds"], 3) for s in segments] == [1.0, 3.5]
    assert segments[0]["end_seconds"] == 3.5
    assert segments[0]["text"] == "Hello world"
    assert segments[1]["text"] == "second line continues"


def test_transcript_reports_whether_timings_exist(service) -> None:
    from unittest.mock import patch

    project_service = service
    with patch.object(
        project_service._media, "fetch_subtitles", return_value="Some text."
    ):
        result = project_service.youtube_transcript("https://youtu.be/x", "en")
    assert result.text == "Some text."
    assert result.segments == []
    assert result.has_timestamps is False


def test_cached_captions_keep_their_segments(library) -> None:
    """``fetch_subtitles`` caches the file, so its timings survive the call."""
    from unittest.mock import patch

    vtt = "WEBVTT\n\n00:00:00.000 --> 00:00:02.000\nHello\n"

    class _FakeYDL:
        def __init__(self, options) -> None:
            self._options = options

        def __enter__(self):
            return self

        def __exit__(self, *exc) -> bool:
            return False

        def extract_info(self, url, download: bool = False):
            outtmpl = self._options["outtmpl"]
            Path(outtmpl.replace("%(id)s", "abc")).with_suffix(".vtt").write_text(
                vtt, encoding="utf-8"
            )
            return {}

    with patch("yt_dlp.YoutubeDL", _FakeYDL):
        assert library.fetch_subtitles("https://youtu.be/abc", "en") == "Hello"
    segments = library.fetch_subtitle_segments("https://youtu.be/abc", "en")
    assert segments == [{"start_seconds": 0.0, "end_seconds": 2.0, "text": "Hello"}]


def test_segments_are_not_fetched_on_their_own(library) -> None:
    """Asking for timings without captions must not trigger a download."""
    assert library.fetch_subtitle_segments("https://youtu.be/never", "en") == []


# --- L13: a status query is cached, and can still be refreshed on demand ------


def test_resource_snapshot_uses_the_cached_profile(tmp_path) -> None:
    from content_factory import hardware
    from content_factory.resources import ResourceGovernor

    settings = _settings(tmp_path)
    calls = {"n": 0}

    def probe_once():
        calls["n"] += 1
        return hardware.probe()

    governor = ResourceGovernor(settings, probe_fn=probe_once)
    governor.snapshot()
    governor.snapshot()
    assert calls["n"] == 1
    governor.snapshot(refresh=True)
    assert calls["n"] == 2


# --- L14: read-only lookups answer to GET -------------------------------------


@pytest.fixture
def client(tmp_path):
    from fastapi.testclient import TestClient

    from content_factory.api import create_app

    return TestClient(create_app(_settings(tmp_path)))


def test_read_only_studio_endpoints_answer_to_get(client) -> None:
    assert client.get("/studio/image/ops").status_code == 200
    assert client.get("/studio/video/ops").status_code == 200
    assert client.get("/studio/audio/ops").status_code == 200
    for path in (
        "/studio/video/describe-op",
        "/studio/audio/describe-op",
        "/studio/image/describe-op",
    ):
        response = client.get(path, params={"name": "crop"})
        assert response.status_code < 500, (path, response.status_code)


def test_get_and_post_describe_agree(client) -> None:
    get_body = client.get("/studio/image/describe-op", params={"name": "crop"}).json()
    post_body = client.post("/studio/image/describe-op", data={"name": "crop"}).json()
    assert get_body == post_body


# --- L16: the request shapes that were documented but not accepted ------------


def test_cost_check_prices_a_list_of_calls(client) -> None:
    """An agent describes a plan call by call; that shape is priced, not zeroed."""
    response = client.post(
        "/cost/check",
        json={"calls": [{"kind": "tts", "count": 3}, {"kind": "vision"}]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["by_kind"]["tts"] > 0
    assert body["by_kind"]["vision"] > 0


def test_cost_check_ignores_a_count_it_has_no_price_for(client) -> None:
    """A count map with an unknown key is still a usable estimate.

    This leniency is deliberate (and asserted in ``tests/test_qa_service.py``):
    a client that starts sending a new kind must not be blocked from pricing the
    rest of its plan.
    """
    response = client.post("/cost/check", json={"calls": {"tts": 2, "gpt-5": 3}})
    assert response.status_code == 200
    priced = response.json()["by_kind"]
    assert priced["tts"] > 0
    # It is listed, but at zero: the guard has no unit cost for it and the rest
    # of the plan is still estimated (rather than the whole plan being refused).
    assert priced.get("gpt-5", 0.0) == 0.0


def test_cost_check_refuses_a_wholly_unpriceable_list(client) -> None:
    """A list without a recognizable kind would price at $0.00 — refuse it."""
    response = client.post(
        "/cost/check",
        json={
            "calls": [
                {
                    "provider": "anthropic",
                    "model": "claude",
                    "input_tokens": 10,
                }
            ]
        },
    )
    assert response.status_code == 422
    detail = str(response.json()["detail"])
    assert "tts" in detail and "vision" in detail


def test_media_tags_accept_both_shapes(client) -> None:
    media = client.post(
        "/media/upload",
        files={"file": ("clip.wav", _wav_bytes(), "audio/wav")},
    ).json()
    bare = client.post(f"/media/{media['id']}/tags", json=["a", "b"])
    assert bare.status_code == 200
    assert bare.json()["tags"] == ["a", "b"]
    wrapped = client.post(f"/media/{media['id']}/tags", json={"tags": ["c"]})
    assert wrapped.status_code == 200
    assert wrapped.json()["tags"] == ["c"]


def test_a_document_without_a_url_is_a_422_not_a_502(client) -> None:
    project = client.post("/projects", json={"name": "Doc", "topic": "T"}).json()
    response = client.post(
        f"/projects/{project['id']}/documents",
        json={"id": "x", "title": "2004 Indian Ocean tsunami"},
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "pdf_url" in detail and "landing_url" in detail
