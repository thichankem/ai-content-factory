from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import TypeAdapter

from content_factory import models
from content_factory.api.routers.qa import build_router
from content_factory.models import (
    AuditRecordRequest,
    BrandCheckRequest,
    CopyrightCheckRequest,
    CostCheckRequest,
    DedupRequest,
    DuckRequest,
    MediaItem,
    MediaKind,
    PlatformCheckRequest,
    SimplifySubtitlesRequest,
    ThumbnailRequest,
    TimelineCommandRequest,
    VideoProject,
    ViralityRequest,
)
from content_factory.services import ContentFactoryService, NotFoundError, QaMixin
from content_factory.services import qa as qa_service
from content_factory.thumbnail import ThumbnailCandidate


@pytest.fixture
def qa_client(service):
    app = FastAPI()
    app.include_router(build_router(service))
    return TestClient(app)


POST_CASES = [
    ("/qa/platform", "qa_platform", PlatformCheckRequest(platform="tiktok"), []),
    ("/qa/brand", "qa_brand", BrandCheckRequest(), []),
    (
        "/qa/copyright",
        "qa_copyright",
        CopyrightCheckRequest(fingerprint="abc", protected=["abc"]),
        [],
    ),
    (
        "/audit/record",
        "audit_record",
        AuditRecordRequest(actor="agent", action="review"),
        {"actor": "agent"},
    ),
    ("/cost/check", "cost_check", CostCheckRequest(calls={"tts": 2}), {"x": 1}),
    ("/media/dedup", "media_dedup", DedupRequest(media_ids=["a"]), [["a"]]),
    (
        "/script/virality",
        "script_virality",
        ViralityRequest(script="Watch this!"),
        {"score": 42},
    ),
    (
        "/render/duck",
        "render_duck",
        DuckRequest(music_media_id="music", voice_media_id="voice"),
        {"out": "mix.mp3"},
    ),
    (
        "/thumbnail/generate",
        "thumbnail_generate",
        ThumbnailRequest(media_id="video"),
        [{"path": "thumb.jpg"}],
    ),
    (
        "/timeline/command",
        "timeline_command",
        TimelineCommandRequest(project=VideoProject(), text="unknown"),
        {"command": {}},
    ),
    (
        "/subtitles/simplify",
        "subtitles_simplify",
        SimplifySubtitlesRequest(captions=["A vehicle"]),
        {"captions": []},
    ),
]


@pytest.mark.parametrize("path,method,payload,result", POST_CASES)
def test_post_routes_delegate_and_models_are_reexported(
    service, qa_client, monkeypatch, path, method, payload, result
) -> None:
    assert isinstance(service, QaMixin)
    model = type(payload)
    assert model.__module__ == "content_factory.models.qa"
    assert model.__name__ in models.__all__
    assert getattr(models, model.__name__) is model
    delegate = Mock(return_value=result)
    monkeypatch.setattr(service, method, delegate)
    response = qa_client.post(path, json=payload.model_dump(mode="json"))
    assert response.status_code == 200
    assert response.json() == result
    delegate.assert_called_once_with(payload)


@pytest.mark.parametrize(
    "path,method,params,args,kwargs",
    [
        ("/audit", "audit_list", {}, (100,), {}),
        ("/audit", "audit_list", {"limit": -1}, (-1,), {}),
        ("/media/search", "media_search", {"q": "ice"}, ("ice",), {"top_k": 10}),
        (
            "/media/search",
            "media_search",
            {"q": "ice", "top_k": 0},
            ("ice",),
            {"top_k": 0},
        ),
    ],
)
def test_get_routes_delegate(
    service, qa_client, monkeypatch, path, method, params, args, kwargs
) -> None:
    delegate = Mock(return_value=[])
    monkeypatch.setattr(service, method, delegate)
    response = qa_client.get(path, params=params)
    assert response.status_code == 200
    assert response.json() == []
    delegate.assert_called_once_with(*args, **kwargs)


@pytest.mark.parametrize(
    "path,method,payload,result",
    [
        case
        for case in POST_CASES
        if case[1]
        in {
            "qa_platform",
            "qa_brand",
            "qa_copyright",
            "cost_check",
            "script_virality",
            "timeline_command",
            "subtitles_simplify",
        }
    ],
)
def test_deterministic_endpoint_service_parity(
    service, qa_client, path, method, payload, result
) -> None:
    expected = json.loads(
        TypeAdapter(object).dump_json(
            getattr(service, method)(payload.model_copy(deep=True))
        )
    )
    response = qa_client.post(path, json=payload.model_dump(mode="json"))
    assert response.status_code == 200
    assert response.json() == expected


@pytest.mark.parametrize(
    "path,payload,field",
    [
        ("/qa/platform", {}, "platform"),
        ("/qa/copyright", {}, "fingerprint"),
        ("/audit/record", {"actor": "", "action": "edit"}, "actor"),
        ("/audit/record", {"actor": "agent", "action": ""}, "action"),
        ("/cost/check", {"calls": {"tts": "bad"}}, "calls"),
        ("/media/dedup", {"media_ids": []}, "media_ids"),
        ("/script/virality", {"script": ""}, "script"),
        ("/render/duck", {"music_media_id": "a"}, "voice_media_id"),
        ("/thumbnail/generate", {"media_id": "a", "top_k": 0}, "top_k"),
        ("/thumbnail/generate", {"media_id": "a", "top_k": 11}, "top_k"),
        ("/timeline/command", {"project": {}, "text": ""}, "text"),
        ("/subtitles/simplify", {"captions": []}, "captions"),
    ],
)
def test_request_validation_unchanged(qa_client, path, payload, field) -> None:
    response = qa_client.post(path, json=payload)
    assert response.status_code == 422
    assert any(field in error["loc"] for error in response.json()["detail"])


@pytest.mark.parametrize(
    "path,method,payload",
    [
        ("/media/dedup", "media_dedup", DedupRequest(media_ids=["missing"])),
        (
            "/render/duck",
            "render_duck",
            DuckRequest(music_media_id="missing", voice_media_id="missing"),
        ),
        (
            "/thumbnail/generate",
            "thumbnail_generate",
            ThumbnailRequest(media_id="missing"),
        ),
    ],
)
def test_missing_media_domain_and_http_errors(
    service, qa_client, path, method, payload
) -> None:
    with pytest.raises(NotFoundError, match="^Media 'missing' not found$"):
        getattr(service, method)(payload)
    response = qa_client.post(path, json=payload.model_dump())
    assert response.status_code == 404
    assert response.json() == {"detail": "Media 'missing' not found"}


def test_invalid_subtitle_level_is_still_a_value_error(service, qa_client) -> None:
    request = SimplifySubtitlesRequest(captions=["text"], level="invalid")
    with pytest.raises(ValueError, match="invalid"):
        service.subtitles_simplify(request)
    with pytest.raises(ValueError, match="invalid"):
        qa_client.post("/subtitles/simplify", json=request.model_dump())


def test_audit_append_order_optional_fields_and_limits(
    service, qa_client, tmp_path
) -> None:
    service.settings.audit_dir = str(tmp_path / "audit")
    first = service.audit_record(AuditRecordRequest(actor="agent", action="check"))
    payload = {
        "actor": "reviewer",
        "action": "note",
        "project_id": "p1",
        "media_id": "m1",
        "prompt": "review this",
        "detail": "no approval",
    }
    response = qa_client.post("/audit/record", json=payload)
    assert response.status_code == 200
    second = response.json()
    assert set(second) == {"ts", *payload}
    assert {key: second[key] for key in payload} == payload
    assert first["project_id"] is first["media_id"] is first["prompt"] is None
    assert first["detail"] is None
    for limit, expected in [
        (100, [second, first]),
        (1, [second]),
        (0, []),
        (-1, [second]),
    ]:
        assert service.audit_list(limit) == expected
        assert qa_client.get("/audit", params={"limit": limit}).json() == expected


@pytest.mark.parametrize(
    "enabled,threshold,confirm",
    [(True, 14, True), (True, 15, False), (False, 0, False)],
)
def test_cost_uses_settings_and_preserves_confirmation_boundary(
    service, qa_client, enabled, threshold, confirm
) -> None:
    settings = service.settings
    settings.cost_guard_enabled = enabled
    settings.cost_guard_threshold_usd = threshold
    for name, value in [
        ("vision", 1),
        ("audio_llm", 2),
        ("tts", 3),
        ("stt", 4),
        ("embedding", 5),
    ]:
        setattr(settings, f"cost_unit_{name}_usd", value)
    request = CostCheckRequest(
        calls={
            "vision": 1,
            "audio_llm": 1,
            "tts": 1,
            "stt": 1,
            "embedding": 1,
            "unknown": 99,
        }
    )
    expected = {
        "estimate_usd": 15,
        "breakdown": {
            "vision": 1,
            "audio_llm": 2,
            "tts": 3,
            "stt": 4,
            "embedding": 5,
            "unknown": 0,
        },
        "needs_confirmation": confirm,
    }
    assert service.cost_check(request) == expected
    assert qa_client.post("/cost/check", json=request.model_dump()).json() == expected


def test_dedup_skips_unhashable_media_and_uses_config(
    service, qa_client, monkeypatch
) -> None:
    monkeypatch.setattr(service, "media_path", lambda media_id: Path(media_id))
    hasher = Mock(side_effect=["abcd", ValueError("not an image"), "abcd"] * 2)
    grouper = Mock(return_value=[["a", "b"]])
    monkeypatch.setattr(qa_service, "image_hash", hasher)
    monkeypatch.setattr(qa_service, "find_near_duplicates", grouper)
    service.settings.dedup_max_distance = 3
    request = DedupRequest(media_ids=["a", "document", "b"])
    assert service.media_dedup(request) == [["a", "b"]]
    assert qa_client.post("/media/dedup", json=request.model_dump()).json() == [
        ["a", "b"]
    ]
    assert hasher.call_count == 6
    grouper.assert_called_with({"a": "abcd", "b": "abcd"}, max_distance=3)


def test_search_transcript_precedence_and_fresh_index(
    service, qa_client, monkeypatch
) -> None:
    items = [
        MediaItem(
            id="a",
            filename="clip",
            kind=MediaKind.VIDEO,
            transcription="aurora",
            text_content="hiddenword",
        ),
        MediaItem(
            id="b", filename="document", kind=MediaKind.DOCUMENT, text_content="fjord"
        ),
        MediaItem(id="c", filename="glacier", kind=MediaKind.IMAGE),
    ]
    monkeypatch.setattr(service, "media_list", lambda: items)
    for query, media_id in [("aurora", "a"), ("fjord", "b"), ("glacier", "c")]:
        result = service.media_search(query, top_k=1)
        assert result[0]["media_id"] == media_id
        assert (
            qa_client.get("/media/search", params={"q": query, "top_k": 1}).json()
            == result
        )
    unmatched = service.media_search("hiddenword")
    assert len(unmatched) == len(items)
    assert all(hit["score"] == 0 for hit in unmatched)


@pytest.mark.parametrize("out", [None, "", "custom.mp3"])
def test_duck_paths_and_output_parity(
    service, qa_client, monkeypatch, tmp_path, out
) -> None:
    monkeypatch.setattr(service, "media_path", lambda media_id: tmp_path / media_id)
    monkeypatch.setattr(qa_service.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(qa_service.uuid, "uuid4", lambda: Mock(hex="a" * 32))
    engine = Mock(return_value="engine-result.mp3")
    monkeypatch.setattr(qa_service, "duck_music_under_speech", engine)
    request = DuckRequest(music_media_id="music", voice_media_id="voice", out=out)
    expected = {"out": "engine-result.mp3"}
    assert service.render_duck(request) == expected
    assert qa_client.post("/render/duck", json=request.model_dump()).json() == expected
    engine.assert_called_with(
        str(tmp_path / "music"),
        str(tmp_path / "voice"),
        out or str(tmp_path / "cf-duck-aaaaaaaaaaaa.mp3"),
    )


def test_thumbnail_engine_arguments_and_serialization(
    service, qa_client, monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(service, "media_path", lambda media_id: tmp_path / media_id)
    monkeypatch.setattr(qa_service.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(qa_service.uuid, "uuid4", lambda: Mock(hex="b" * 32))
    candidate = ThumbnailCandidate("thumb.jpg", 1.5, 0.9, 0.8)
    engine = Mock(return_value=[candidate])
    monkeypatch.setattr(qa_service, "generate_thumbnails", engine)
    request = ThumbnailRequest(media_id="video", top_k=2, overlays=["Watch"])
    assert service.thumbnail_generate(request) == [candidate.__dict__]
    response = qa_client.post("/thumbnail/generate", json=request.model_dump())
    assert response.json() == [candidate.__dict__]
    engine.assert_called_with(
        str(tmp_path / "video"),
        str(tmp_path / "cf-thumbs-bbbbbbbbbbbb"),
        top_k=2,
        overlays=("Watch",),
    )


def test_qa_does_not_approve_or_persist_timeline(
    service, qa_client, sample_project, tmp_path
) -> None:
    service.settings.audit_dir = str(tmp_path / "audit")
    before = service.get_project(sample_project.id).model_dump(mode="json")
    for path, _, request, _ in POST_CASES:
        if path in {"/media/dedup", "/render/duck", "/thumbnail/generate"}:
            continue
        response = qa_client.post(path, json=request.model_dump(mode="json"))
        assert response.status_code == 200
    assert service.get_project(sample_project.id).model_dump(mode="json") == before
    assert service.get_project(sample_project.id).source_rights_confirmed is False
    assert QaMixin in ContentFactoryService.__mro__
