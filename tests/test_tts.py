"""Tests for the text-to-speech voiceover integration."""

from __future__ import annotations

import asyncio

import pytest

from content_factory import timeline
from content_factory.config import Settings
from content_factory.models import (
    ApprovalCreate,
    ProjectCreate,
    ProjectStatus,
    ScriptUpdate,
    VideoProject,
    VideoScene,
)
from content_factory.service import ContentFactoryService, StateConflictError
from content_factory.tts import (
    EdgeTTSProvider,
    GTTSProvider,
    TTSEngine,
    mp3_duration,
    resolve_voice,
)

SCRIPT = (
    "[Hook]\nHave you noticed how morning light shapes your day?\n\n"
    "[Context]\nMost people walk past it.\n\n"
    "[Payoff]\nThat is the quiet power hiding in plain sight."
)


def test_resolve_voice_mapping() -> None:
    assert resolve_voice("vi") == "vi-VN-HoaiMyNeural"
    assert resolve_voice("vi-VN") == "vi-VN-HoaiMyNeural"
    assert resolve_voice("en") == "en-US-JennyNeural"
    assert resolve_voice("unknown-lang") == "en-US-JennyNeural"


def test_mp3_duration_zero_for_garbage() -> None:
    assert mp3_duration(b"not an mp3") == 0.0


def test_tts_engine_estimates_duration_on_parse_failure(monkeypatch) -> None:
    engine = TTSEngine(Settings(tts_engine="gtts"))

    async def fake_gtts(self, text, language):
        return b"fake-mp3-bytes"

    monkeypatch.setattr(GTTSProvider, "synthesize", fake_gtts)
    monkeypatch.setattr("content_factory.tts.mp3_duration", lambda data: 0.0)
    data, duration, name = asyncio.run(engine.synthesize("Hello world", "en"))
    assert name == "gtts"
    assert duration >= 1.0
    assert len(data) > 0


def test_tts_engine_falls_back_to_gtts_when_edge_fails(monkeypatch) -> None:
    engine = TTSEngine(Settings(tts_engine="edge"))
    calls = {"edge": 0, "gtts": 0}

    async def fake_edge(self, text, language):
        calls["edge"] += 1
        raise RuntimeError("edge down")

    async def fake_gtts(self, text, language):
        calls["gtts"] += 1
        return b"fake-mp3-bytes"

    monkeypatch.setattr(EdgeTTSProvider, "synthesize", fake_edge)
    monkeypatch.setattr(GTTSProvider, "synthesize", fake_gtts)
    data, duration, name = asyncio.run(engine.synthesize("Hello", "en"))
    assert name == "gtts"
    assert calls["edge"] == 1
    assert calls["gtts"] == 1


def test_voiceover_worker_syncs_scene_durations(
    settings: Settings, monkeypatch
) -> None:
    from content_factory.tts import TTSEngine

    service = ContentFactoryService(settings)
    project = service.create_project(
        ProjectCreate(name="V", topic="topic", duration_target_seconds=30)
    )
    service.update_script(
        project.id, ScriptUpdate(script=SCRIPT, source_rights_confirmed=True)
    )
    service.approve(project.id, ApprovalCreate(stage="script", verdict="approved"))
    monkeypatch.setattr(service, "_spawn_worker", lambda project_id: None)
    service.start_generation(project.id)
    service.complete_generation(project.id)
    assert project.video_project is not None
    original_revision = project.video_project.revision
    original_durations = [s.duration_seconds for s in project.video_project.scenes]

    async def fake_synthesize(self, text, language, pitch=1.0):
        return b"fake-mp3", 2.5, "edge-tts"

    monkeypatch.setattr(TTSEngine, "synthesize", fake_synthesize)
    service._synthesize_voiceover(project.id)

    refreshed = service.get_project(project.id)
    assert refreshed.voiceover is not None
    assert len(refreshed.voiceover.tracks) == 3
    assert refreshed.voiceover.engine == "edge-tts"
    assert refreshed.video_project is not None
    assert refreshed.video_project.revision == original_revision + 1
    assert [
        s.duration_seconds for s in project.video_project.scenes
    ] == original_durations
    for scene, original in zip(
        refreshed.video_project.scenes, original_durations, strict=True
    ):
        assert scene.duration_seconds == pytest.approx(2.9)
        assert scene.duration_seconds != original


@pytest.fixture
def voiced_project(service, monkeypatch):
    project = service.create_project(ProjectCreate(name="Voice", topic="City"))
    project.status = ProjectStatus.VIDEO_REVIEW
    project.video_project = VideoProject(
        revision=23,
        scenes=[
            VideoScene(id="first", label="First", text="Hello", duration_seconds=3),
            VideoScene(
                id="second",
                label="Second",
                text="",
                narration="Goodbye",
                duration_seconds=4,
            ),
        ],
    )

    async def synthesize(self, text, language, pitch=1.0):
        return b"original audio", 2.5, "fake"

    monkeypatch.setattr(TTSEngine, "synthesize", synthesize)
    service._synthesize_voiceover(project.id)
    return service.get_project(project.id)


def test_voiceover_normalizes_and_preserves_published_policy(
    service, voiced_project, monkeypatch
):
    project = voiced_project
    project.status = ProjectStatus.PUBLISHED
    project.video_project.aspect_ratio = "invalid"
    before = project.model_copy(deep=True)

    async def synthesize(self, text, language, pitch=1.0):
        return b"new audio", 90.0, "fake"

    monkeypatch.setattr(TTSEngine, "synthesize", synthesize)
    service.synthesize_voiceover(project.id)
    result = service.get_project(project.id)
    assert result.error is None
    assert result.video_project.revision == before.video_project.revision + 1
    assert result.video_project.aspect_ratio == "9:16"
    assert all(scene.duration_seconds == 60 for scene in result.video_project.scenes)
    assert result.status == ProjectStatus.PUBLISHED
    assert result.source_rights_confirmed is False
    assert result.approvals == before.approvals
    assert project == before
    assert service.voiceover_path(project.id, "first").read_bytes() == b"new audio"


@pytest.mark.parametrize("failure", ["tts", "normalize", "save"])
def test_failed_voiceover_preserves_timeline_bundle_and_audio(
    service, voiced_project, monkeypatch, failure
):
    before = voiced_project.model_copy(deep=True)
    original_normalize = timeline.normalize
    calls = 0

    async def synthesize(self, text, language, pitch=1.0):
        nonlocal calls
        calls += 1
        if failure == "tts" and calls == 2:
            raise RuntimeError("synthesis failed")
        return b"partial new audio", 9.0, "fake"

    def normalize(video):
        if calls:
            video.scenes[0].text = "partial normalization"
            raise RuntimeError("normalization failed")
        return original_normalize(video)

    original_save = service.store.save

    def save(project):
        if project.error is None:
            raise RuntimeError("save failed")
        return original_save(project)

    monkeypatch.setattr(TTSEngine, "synthesize", synthesize)
    if failure == "normalize":
        monkeypatch.setattr(
            "content_factory.services.voice.timeline.normalize", normalize
        )
    elif failure == "save":
        monkeypatch.setattr(service.store, "save", save)
    service._synthesize_voiceover(before.id)
    result = service.get_project(before.id)
    assert "failed" in result.error.lower()
    assert result.video_project == before.video_project
    assert result.voiceover == before.voiceover
    assert voiced_project == before
    assert service.voiceover_path(before.id, "first").read_bytes() == b"original audio"


@pytest.mark.parametrize(
    "change", ["edit", "rebuild", "legacy_edit", "language", "status"]
)
def test_voiceover_rejects_stale_snapshot_without_losing_edits(
    service, voiced_project, monkeypatch, change
):
    before = voiced_project.model_copy(deep=True)
    latest = None

    async def synthesize(self, text, language, pitch=1.0):
        nonlocal latest
        if latest is None:
            if change == "edit":
                service.reverse_scene(before.id, "first")
            elif change == "rebuild":
                service.build_video_project(before.id)
            elif change == "legacy_edit":
                service.get_project(before.id).video_project.scenes[
                    0
                ].text = "Live edit"
            elif change == "language":
                service.get_project(before.id).target_language = "en"
            else:
                service.get_project(before.id).status = ProjectStatus.SCRIPT_REVIEW
            latest = service.get_project(before.id).model_copy(deep=True)
        return b"stale audio", 9.0, "fake"

    monkeypatch.setattr(TTSEngine, "synthesize", synthesize)
    service._synthesize_voiceover(before.id)
    result = service.get_project(before.id)
    assert result.error.startswith("Voiceover failed:")
    assert result.video_project == latest.video_project
    assert result.target_language == latest.target_language
    assert result.status == latest.status
    assert result.voiceover == before.voiceover
    assert service.voiceover_path(before.id, "first").read_bytes() == b"original audio"


def test_voiceover_preserves_unrelated_edits_during_synthesis(
    service, voiced_project, monkeypatch
):
    before = voiced_project.model_copy(deep=True)

    async def synthesize(self, text, language, pitch=1.0):
        current = service.get_project(before.id).model_copy(deep=True)
        current.name = "Renamed during synthesis"
        service.store.save(current)
        return b"new audio", 4.0, "fake"

    monkeypatch.setattr(TTSEngine, "synthesize", synthesize)
    result = service.synthesize_voiceover(before.id)
    assert result.error is None
    assert result.name == "Renamed during synthesis"
    assert result.video_project.revision == before.video_project.revision + 1


@pytest.mark.parametrize("entrypoint", ["generate_voiceover", "synthesize_voiceover"])
def test_voiceover_cannot_edit_a_preapproval_timeline(
    service, voiced_project, entrypoint
):
    voiced_project.status = ProjectStatus.SCRIPT_REVIEW
    before = voiced_project.model_copy(deep=True)
    with pytest.raises(StateConflictError):
        getattr(service, entrypoint)(before.id)
    assert service.get_project(before.id) == before


def test_generate_voiceover_requires_video_project(
    service: ContentFactoryService,
) -> None:
    project = service.create_project(ProjectCreate(name="V", topic="t"))
    with pytest.raises(StateConflictError):
        service.generate_voiceover(project.id)


def test_generate_voiceover_disabled(settings: Settings) -> None:
    service = ContentFactoryService(settings.model_copy(update={"tts_enabled": False}))
    project = service.create_project(ProjectCreate(name="V", topic="t"))
    with pytest.raises(StateConflictError):
        service.generate_voiceover(project.id)
