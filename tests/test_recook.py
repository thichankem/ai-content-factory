"""Tests for the content re-cook pipeline (read -> re-word -> new project)."""

from __future__ import annotations

from unittest.mock import patch

from content_factory import voice_engine
from content_factory.media import MediaLibrary
from content_factory.models import (
    MediaItem,
    MediaKind,
    ProjectStatus,
    ReCookMode,
    ReCookRequest,
)
from content_factory.recook import RecookPipeline, build_recooked_script
from content_factory.store import Store

TRANSCRIPT = (
    "The Battle of Stalingrad lasted from August 1942 to February 1943. "
    "It was one of the bloodiest battles in history. "
    "Soviet forces surrounded the German Sixth Army. "
    "The surrender marked a turning point in the war. "
    "Logistics and winter played a huge role in the outcome. "
    "Ordinary soldiers endured terrible conditions. "
    "The city became a symbol of resistance. "
    "Historians still study its lessons today."
)


def test_build_recooked_script_has_sections() -> None:
    script = build_recooked_script(TRANSCRIPT, "Stalingrad", 60, ReCookMode.BALANCED)
    for label in ["[Hook]", "[Context]", "[Turn]", "[Payoff]", "[CTA]"]:
        assert label in script, label
    # The re-worded cut must not be a verbatim copy of the source.
    assert "Battle of Stalingrad lasted from August" not in script


def test_build_recooked_script_condenses() -> None:
    condense = build_recooked_script(TRANSCRIPT, "Stalingrad", 20, ReCookMode.CONDENSE)
    balanced = build_recooked_script(TRANSCRIPT, "Stalingrad", 60, ReCookMode.BALANCED)
    assert len(condense) <= len(balanced)


def test_pipeline_creates_new_project(settings) -> None:
    media = MediaLibrary(settings.media_dir)
    pipeline = RecookPipeline(settings, media)
    store = Store()

    item = MediaItem(
        id="src1",
        filename="source.mp4",
        kind=MediaKind.VIDEO,
        transcription=TRANSCRIPT,
        language="en",
    )
    media.add_item(item)

    result = pipeline.run(
        "src1",
        ReCookRequest(
            new_title="Stalingrad: The Turning Point",
            language="en",
            target_seconds=60,
            mode=ReCookMode.BALANCED,
        ),
        store,
    )
    assert result.project_id
    assert result.status == "script_review"
    assert result.new_title == "Stalingrad: The Turning Point"
    assert "[Hook]" in result.script

    project = store.get(result.project_id)
    assert project is not None
    assert project.status == ProjectStatus.SCRIPT_REVIEW
    assert project.source_rights_confirmed is False  # never auto-confirmed
    assert project.duration_target_seconds == 60


def test_pipeline_prepares_document_text(settings) -> None:
    media = MediaLibrary(settings.media_dir)
    pipeline = RecookPipeline(settings, media)
    store = Store()
    item = media.upload(
        "brief.txt", b"The siege lasted months. Winter came early.", language="en"
    )
    prepared = pipeline.prepare_source(item.id)
    assert prepared.text_content
    result = pipeline.run(
        item.id, ReCookRequest(new_title="Siege", target_seconds=30), store
    )
    assert result.script
    assert result.project_id


def test_pipeline_denoise_transcribes_clean_audio(settings) -> None:
    """denoise=True denoises the source audio before transcribing it."""
    media = MediaLibrary(settings.media_dir)
    pipeline = RecookPipeline(settings, media)
    item = media.upload(
        "noisy.mp3",
        b"\xff\xfb\x90\x64" * 4096,  # any bytes; denoise+transcribe are mocked
        language="en",
    )
    item.kind = MediaKind.VIDEO
    media.update(item)

    denoised_wav = voice_engine.encode_pcm(
        (0.5 * __import__("numpy").ones(1600)).astype("float32"), 44100, "wav"
    )
    with (
        patch.object(
            voice_engine,
            "denoise_audio",
            return_value=(denoised_wav, {"method": "spectral_gating"}),
        ) as denoise_mock,
        patch.object(
            media, "transcribe_file", return_value=("Clean transcript.", [])
        ) as transcribe_mock,
    ):
        prepared = pipeline.prepare_source(item.id, ReCookRequest(denoise=True))

    denoise_mock.assert_called_once()
    transcribe_mock.assert_called_once()
    assert prepared.transcription == "Clean transcript."


def test_pipeline_without_denoise_skips_it(settings) -> None:
    """denoise defaults to False: the normal transcribe path is used."""
    media = MediaLibrary(settings.media_dir)
    pipeline = RecookPipeline(settings, media)
    item = media.upload("plain.mp3", b"\xff\xfb\x90\x64" * 4096, language="en")
    item.kind = MediaKind.VIDEO
    media.update(item)
    with patch.object(media, "transcribe", return_value=item) as transcribe_mock:
        pipeline.prepare_source(item.id, ReCookRequest())
    transcribe_mock.assert_called_once()
