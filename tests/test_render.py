from __future__ import annotations

import json
import shutil
import subprocess
import time

import pytest

from content_factory.render import render_video_file
from content_factory.scenes import build_video_project
from content_factory.timeline import compile_render_plan


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is not installed")
def test_render_video_file_creates_probeable_webm(tmp_path) -> None:
    project = build_video_project("[Hook]\nA real render test.", 5, "en")
    plan = compile_render_plan(project, "render-test")
    output = render_video_file(plan, tmp_path / "render-test.webm")

    assert output.is_file()
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_format", "-of", "json", str(output)],
        capture_output=True,
        text=True,
        check=True,
    )
    metadata = json.loads(probe.stdout)
    assert float(metadata["format"]["duration"]) >= 4.9


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is not installed")
def test_render_handles_apostrophes_and_commas(tmp_path) -> None:
    """Regression: narration with apostrophes/commas must not break drawtext.

    Inline ``text='...'`` in an ffmpeg filter aborts with "Option not found"
    when the text contains an apostrophe (e.g. "Napoleon's army"). The renderer
    must use a textfile so arbitrary narration renders reliably.
    """
    from content_factory.models import (
        ColorGrade,
        EntranceEffect,
        ExitEffect,
        KenBurns,
        RenderPlan,
        RenderStep,
        SceneEffect,
        TextPosition,
        TextStyle,
        VideoFilter,
        VideoTransition,
    )

    step = RenderStep(
        index=0,
        scene_id="s1",
        label="Context",
        start_seconds=0,
        end_seconds=2,
        duration_seconds=2,
        transition_in=VideoTransition.CUT,
        transition_seconds=0,
        filter=VideoFilter.NONE,
        effect=SceneEffect.NONE,
        grade=ColorGrade.NONE,
        ken_burns=KenBurns.NONE,
        background="#111827",
        text=(
            "The Battle of Waterloo took place on June 18, 1815. Napoleon's army fell."
        ),
        text_position=TextPosition.CENTER,
        text_style=TextStyle.NORMAL,
        text_color="#ffffff",
        font_size=48,
        entrance=EntranceEffect.FADE,
        exit=ExitEffect.NONE,
    )
    plan = RenderPlan(
        project_id="apostrophe",
        aspect_ratio="9:16",
        width=320,
        height=568,
        fps=10,
        total_seconds=2,
        steps=[step],
    )
    output = render_video_file(plan, tmp_path / "apostrophe.webm")
    assert output.is_file() and output.stat().st_size > 0


def test_render_endpoint_persists_and_serves_webm(client) -> None:
    project = client.post(
        "/projects",
        json={
            "name": "Render endpoint",
            "topic": "A short rendering integration test",
            "target_language": "en",
            "duration_target_seconds": 5,
        },
    ).json()
    project_id = project["id"]
    script = "[Hook]\nA real server render.\n[Payoff]\nThe file exists."
    project = client.put(
        f"/projects/{project_id}/script",
        json={"script": script, "source_rights_confirmed": True},
    ).json()
    assert project["status"] == "script_review"
    project = client.post(
        f"/projects/{project_id}/approvals",
        json={"stage": "script", "verdict": "approved"},
    ).json()
    assert project["status"] == "script_approved"
    client.post(f"/projects/{project_id}/generate")

    for _ in range(20):
        project = client.get(f"/projects/{project_id}").json()
        if project["status"] == "video_review":
            break
        time.sleep(0.02)
    assert project["status"] == "video_review"

    rendered = client.post(f"/projects/{project_id}/render")
    assert rendered.status_code == 200
    assert rendered.json()["video"]["format"] == "webm"
    video = client.get(f"/projects/{project_id}/video")
    assert video.status_code == 200
    assert video.content[:4] == b"\x1a\x45\xdf\xa3"


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is not installed")
def test_render_with_background_video_has_audio(tmp_path) -> None:
    """The enhanced renderer mixes voiceover + music under a moving backdrop.

    Regression: a re-cooked video must ship with a real audio track (VP9 video
    + Opus audio), not silent colour cards.
    """
    from content_factory.models import (
        AudioTrackPlan,
        ColorGrade,
        EntranceEffect,
        ExitEffect,
        KenBurns,
        RenderPlan,
        RenderStep,
        SceneEffect,
        TextPosition,
        TextStyle,
        VideoFilter,
        VideoTransition,
    )

    # A tiny real background video.
    bg = tmp_path / "bg.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=320x568:r=10:d=3",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            str(bg),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    # A short music bed.
    music = tmp_path / "music.ogg"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=3",
            "-c:a",
            "libvorbis",
            str(music),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    step = RenderStep(
        index=0,
        scene_id="s1",
        label="Hook",
        start_seconds=0,
        end_seconds=3,
        duration_seconds=3,
        transition_in=VideoTransition.CUT,
        transition_seconds=0,
        filter=VideoFilter.NONE,
        effect=SceneEffect.NONE,
        grade=ColorGrade.NONE,
        ken_burns=KenBurns.NONE,
        background="#111827",
        image_url=None,
        text="Real footage with sound.",
        text_position=TextPosition.CENTER,
        text_style=TextStyle.NORMAL,
        text_color="#ffffff",
        font_size=32,
        entrance=EntranceEffect.FADE,
        exit=ExitEffect.NONE,
        narration_url=None,
        volume=1.0,
    )
    plan = RenderPlan(
        project_id="bg",
        aspect_ratio="9:16",
        width=320,
        height=568,
        fps=10,
        total_seconds=3,
        steps=[step],
        audio=[AudioTrackPlan(kind="music", enabled=True, volume=0.3)],
    )
    out = tmp_path / "bg.webm"
    render_video_file(plan, out, music_path=music, background_video=bg)
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=codec_type",
            "-of",
            "csv",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    types = [line.split(",")[-1] for line in probe.stdout.strip().splitlines()]
    assert "video" in types and "audio" in types


def test_music_gain_zero_stays_muted() -> None:
    from content_factory.models import AudioTrackPlan
    from content_factory.render import _music_volume

    plan = compile_render_plan(build_video_project("A mute regression.", 5, "en"))
    plan.audio = [AudioTrackPlan(kind="music", enabled=True, volume=0.0)]
    assert _music_volume(plan) == 0.0


@pytest.fixture
def tiny_media(tmp_path):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("ffmpeg and ffprobe required")
    video = tmp_path / "red.mp4"
    audio = tmp_path / "tone.wav"
    for target, source in (
        (video, "color=c=red:s=160x120:r=24:d=2"),
        (audio, "sine=frequency=440:duration=1"),
    ):
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-filter_threads",
                "1",
                "-f",
                "lavfi",
                "-i",
                source,
                "-threads",
                "1",
                str(target),
            ],
            capture_output=True,
            check=True,
        )
    return video, audio


@pytest.mark.parametrize("background", [False, True])
@pytest.mark.parametrize("gain", [0.0, 1.0])
def test_mp4_later_narration_and_mute(tmp_path, tiny_media, background, gain):
    import array

    from content_factory.models import VideoProject, VideoScene

    video, audio = tiny_media
    project = VideoProject(
        scenes=[
            VideoScene(id="first", label="First", text="", duration_seconds=1),
            VideoScene(
                id="later", label="Later", text="", duration_seconds=1, volume=gain
            ),
        ]
    )
    if not background:
        project.scenes[0].video_url = "video"
        project.scenes[1].video_url = "video"
    plan = compile_render_plan(project, narration_urls={"later": "voice"})
    plan.width, plan.height = 160, 120
    output = render_video_file(
        plan,
        tmp_path / "test.mp4",
        export_format="mp4",
        resolve_media=lambda ref: {"video": video, "voice": audio}[ref],
        background_video=video if background else None,
    )
    streams = json.loads(
        subprocess.run(
            ["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(output)],
            capture_output=True,
            check=True,
        ).stdout
    )["streams"]
    assert {s["codec_name"] for s in streams} == {"h264", "aac"}
    decoded = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(output),
            "-map",
            "0:a",
            "-ac",
            "1",
            "-ar",
            "8000",
            "-f",
            "f32le",
            "pipe:1",
        ],
        capture_output=True,
        check=True,
    ).stdout
    samples = array.array("f")
    samples.frombytes(decoded)
    early = max(abs(v) for v in samples[1600:6400])
    later = max(abs(v) for v in samples[9600:14400])
    assert early < 0.001
    assert later < 0.001 if gain == 0 else later > 0.01


def test_compile_prefers_scene_video_without_mutation():
    from content_factory.models import VideoProject, VideoScene

    project = VideoProject(
        scenes=[
            VideoScene(
                id="one", label="One", text="", video_url="clip", image_url="image"
            )
        ]
    )
    original = project.model_copy(deep=True)
    assert compile_render_plan(project).steps[0].image_url == "clip"
    assert project == original


def test_renderer_preserves_old_artifact_on_error(tmp_path, monkeypatch):
    from content_factory.render import RenderError

    plan = compile_render_plan(build_video_project("Test", 5, "en"))
    output = tmp_path / "old.mp4"
    output.write_bytes(b"old artifact")
    monkeypatch.setattr(
        "content_factory.render.subprocess.run",
        lambda *a, **kw: subprocess.CompletedProcess([], 1, "", "synthetic failure"),
    )
    with pytest.raises(RenderError, match="synthetic failure"):
        render_video_file(plan, output, export_format="mp4", ffmpeg_binary="ffmpeg")
    assert output.read_bytes() == b"old artifact"
    assert not list(tmp_path.glob(".render-*"))


def _review_project(service):
    from content_factory.models import (
        ApprovalCreate,
        ProjectCreate,
        ScriptUpdate,
        VideoProject,
        VideoScene,
    )

    project = service.create_project(ProjectCreate(name="Export", topic="Test"))
    service.update_script(
        project.id, ScriptUpdate(script="Test", source_rights_confirmed=True)
    )
    service.approve(project.id, ApprovalCreate(stage="script", verdict="approved"))
    service.produce_video(project.id)
    service.update_video_project(
        project.id,
        VideoProject(
            scenes=[
                VideoScene(id="one", label="One", text="", duration_seconds=1),
            ]
        ),
    )
    return service.get_project(project.id)


def test_mp4_tool_api_and_download(service, tiny_media):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from content_factory.api.routers.timeline import build_router
    from content_factory.api.routers.tools import build_router as tools_router

    service.settings.render_max_dimension = 160
    service.settings.tts_enabled = False
    project = _review_project(service)
    source, tone = tiny_media
    media = service.media_upload(source.name, source.read_bytes())
    edited = service._edited_dir / "mix.wav"
    edited.write_bytes(tone.read_bytes())
    project.video_project.scenes[0].video_url = media.id
    app = FastAPI()
    app.include_router(build_router(service))
    app.include_router(tools_router(service))
    with TestClient(app) as client:
        response = client.post(
            "/tools/call",
            json={
                "tool": "render_video",
                "args": {
                    "project_id": project.id,
                    "export_format": "mp4",
                    "audio_ref": "/edited/mix.wav",
                },
            },
        )
        assert response.status_code == 200, response.text
        current = service.get_project(project.id)
        assert current.status == "video_review"
        assert current.approvals == project.approvals
        assert current.video.format == "mp4"
        download = client.get(f"/projects/{project.id}/video?download=true")
        assert download.headers["content-type"] == "video/mp4"
        assert f"{project.id}.mp4" in download.headers["content-disposition"]
        assert b"ftyp" in download.content[:32]
        assert (
            client.post(
                f"/projects/{project.id}/render", json={"export_format": "avi"}
            ).status_code
            == 422
        )
        response = client.post(
            f"/projects/{project.id}/render", json={"export_format": "mp4"}
        )
        assert response.status_code == 200, response.text
        assert client.post(f"/projects/{project.id}/render").status_code == 200
        assert (
            client.get(f"/projects/{project.id}/video").headers["content-type"]
            == "video/webm"
        )


def test_export_rejects_approved_and_stale_project(service, monkeypatch):
    from content_factory.models import ApprovalCreate
    from content_factory.services.errors import StateConflictError

    project = _review_project(service)
    original = project.model_copy(deep=True)
    output = service._edited_dir.parent / "videos" / f"{project.id}.webm"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(b"old")

    def stale(plan, target, **kwargs):
        target.write_bytes(b"new")
        current = service.get_project(project.id)
        current.video_project.revision += 1
        service.store.save(current)

    monkeypatch.setattr("content_factory.services.production.render_video_file", stale)
    with pytest.raises(StateConflictError, match="changed"):
        service.render_video(project.id)
    assert output.read_bytes() == b"old"
    assert service.get_project(project.id).video == original.video
    service.approve(project.id, ApprovalCreate(stage="video", verdict="approved"))
    with pytest.raises(StateConflictError, match="video_approved"):
        service.render_video(project.id)
    from content_factory.models import PublishCreate

    service.publish(project.id, PublishCreate())
    with pytest.raises(StateConflictError, match="published"):
        service.render_video(project.id)


def test_explicit_music_and_local_refs(service, tiny_media):
    from content_factory.services.errors import NotFoundError

    project = _review_project(service)
    _, tone = tiny_media
    asset = service._edited_dir / "bed.wav"
    asset.write_bytes(tone.read_bytes())
    project.video_project.background_music = True
    project.video_project.background_music_url = "/edited/bed.wav"
    assert service._music_bed_for(project) == asset.resolve()
    for ref in ("https://example.invalid/bed.wav", "/edited/../bed.wav"):
        with pytest.raises(NotFoundError):
            service._resolve_render_ref(ref)


def test_mcp_manifest_schema_parity():
    import ast
    from pathlib import Path

    from content_factory.agent_tools import build_tool_manifest

    tree = ast.parse(
        (Path(__file__).parents[1] / "mcp_server.py").read_text(encoding="utf-8")
    )
    function = next(
        n
        for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name == "factory_list_tools"
    )
    function.decorator_list = []
    namespace = {"build_tool_manifest": build_tool_manifest}
    exec(
        compile(ast.Module(body=[function], type_ignores=[]), "mcp_manifest", "exec"),
        namespace,
    )
    assert json.loads(namespace["factory_list_tools"]()) == build_tool_manifest()
    tool = next(
        t for t in build_tool_manifest()["tools"] if t["name"] == "render_video"
    )
    assert tool["input_schema"]["properties"]["export_format"]["enum"] == [
        "webm",
        "mp4",
    ]
