from __future__ import annotations

from dataclasses import asdict, fields
from types import MappingProxyType

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from content_factory import seo
from content_factory.models import (
    AbArmInput,
    CompetitorVideoInput,
    SeoEngagementInput,
    SeoPackInput,
)
from content_factory.service import ContentFactoryService
from content_factory.services.seo import (
    _engagement_from_mapping,
    arm_from_mapping,
    competitor_from_mapping,
    pack_from_mapping,
)

BOOLEAN_FIELDS = (
    "thumbnail_present",
    "has_captions",
    "has_chapters",
    "has_end_screen",
    "sound_trending",
    "beat_synced",
    "loop_friendly",
    "text_in_safe_zone",
    "watermark",
    "comment_prompt",
    "duet_stitch_enabled",
)


@pytest.mark.parametrize("field", BOOLEAN_FIELDS)
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("false", False),
        ("False", False),
        ("0", False),
        ("off", False),
        ("no", False),
        (False, False),
        (0, False),
        ("true", True),
        ("1", True),
        ("on", True),
        (True, True),
    ],
)
def test_boolean_mapping_parity(field: str, value: object, expected: bool) -> None:
    payload = {field: value}
    pack = pack_from_mapping(payload)
    assert getattr(pack, field) is expected
    assert pack == SeoPackInput.model_validate(payload).to_engine()


@pytest.mark.parametrize("field", BOOLEAN_FIELDS)
def test_boolean_null_parity(field: str) -> None:
    payload = {field: None}
    if field in {"has_chapters", "comment_prompt"}:
        with pytest.raises(ValidationError):
            pack_from_mapping(payload)
        with pytest.raises(ValidationError):
            SeoPackInput.model_validate(payload)
    else:
        assert (
            pack_from_mapping(payload)
            == SeoPackInput.model_validate(payload).to_engine()
        )
        assert getattr(pack_from_mapping(payload), field) is None


def test_pack_defaults_and_complete_field_surface() -> None:
    assert pack_from_mapping(None) == pack_from_mapping({}) == seo.Pack()
    assert SeoPackInput().to_engine() == seo.Pack()
    assert set(SeoPackInput.model_fields) == {field.name for field in fields(seo.Pack)}
    assert pack_from_mapping({"caption_source": "manual"}).caption_source == "manual"
    assert pack_from_mapping({"ignored": "value"}) == seo.Pack()
    assert pack_from_mapping({"engagement": {}}).engagement == seo.Engagement()
    assert pack_from_mapping({"engagement": None}).engagement is None
    assert pack_from_mapping({"playlist": None}).playlist is None
    assert pack_from_mapping({"playlist": ""}).playlist == ""


def test_numeric_sequence_and_nested_mapping_parity() -> None:
    payload = {
        "title": "Điện Biên Phủ",
        "caption_source": "manual",
        "tags": ("history", "archive"),
        "hashtags": ["#history"],
        "keywords": ["Điện Biên Phủ"],
        "on_screen_text": ["Evidence"],
        "duration_seconds": "30.5",
        "intro_seconds": "0",
        "cuts_per_minute": "20",
        "chapter_count": "0",
        "publish_hour": "0",
        "audience_hours": ["0", "23"],
        "bpm": "120",
        "series_part": "1",
        "watermark": "false",
        "engagement": {
            "views": "100",
            "impressions": "1000",
            "watch_time_seconds": "2000",
            "average_view_seconds": "20",
            "completion_rate": "1.5",
            "ignored": 1,
        },
        "ignored": "value",
    }
    pack = pack_from_mapping(MappingProxyType(payload))
    assert pack == SeoPackInput.model_validate(payload).to_engine()
    assert pack.duration_seconds == 30.5
    assert pack.publish_hour == 0
    assert pack.chapter_count == 0
    assert pack.audience_hours == (0, 23)
    assert pack.engagement is not None
    assert pack.engagement.views == 100
    assert pack.engagement.completion_rate == 1.5
    assert pack.tags == ("history", "archive")
    assert pack_from_mapping(asdict(pack)) == pack


@pytest.mark.parametrize(
    "payload",
    [
        {"watermark": "invalid"},
        {"chapter_count": -1},
        {"publish_hour": 24},
        {"series_part": 0},
        {"duration_seconds": -1},
        {"duration_seconds": "bad"},
        {"duration_seconds": ""},
        {"tags": "single"},
        {"tags": None},
        {"tags": [1]},
        {"title": None},
        {"engagement": "invalid"},
        {"engagement": {"views": -1}},
        {"engagement": {"views": "2.5"}},
        {"engagement": {"completion_rate": 1.6}},
        {"has_chapters": None},
    ],
)
def test_invalid_pack_rejected_identically(payload: dict) -> None:
    with pytest.raises(ValidationError) as mapping_error:
        pack_from_mapping(payload)
    with pytest.raises(ValidationError) as model_error:
        SeoPackInput.model_validate(payload)
    assert mapping_error.value.errors() == model_error.value.errors()


@pytest.mark.parametrize(
    ("converter", "model", "payload"),
    [
        (
            arm_from_mapping,
            AbArmInput,
            {
                "name": "control",
                "impressions": "100",
                "clicks": "4",
                "mean_value": "0.4",
                "sd_value": "0.1",
            },
        ),
        (
            competitor_from_mapping,
            CompetitorVideoInput,
            {
                "title": "History",
                "views": "200",
                "subscribers": "100",
                "days_old": "0",
                "duration_seconds": "30.5",
            },
        ),
        (
            _engagement_from_mapping,
            SeoEngagementInput,
            {
                "views": "200",
                "likes": "0",
                "watch_time_seconds": "100.5",
                "completion_rate": "1.5",
            },
        ),
    ],
)
def test_row_conversion_parity(converter, model, payload: dict) -> None:
    payload["ignored"] = "value"
    assert (
        converter(MappingProxyType(payload))
        == model.model_validate(payload).to_engine()
    )
    assert converter(payload) == converter(model.model_validate(payload).model_dump())


@pytest.mark.parametrize(
    ("converter", "model", "payload"),
    [
        (arm_from_mapping, AbArmInput, {"name": "a", "views": -1}),
        (arm_from_mapping, AbArmInput, {"name": "a", "views": "bad"}),
        (arm_from_mapping, AbArmInput, {"name": "a", "views": "2.5"}),
        (arm_from_mapping, AbArmInput, {"name": "a", "sd_value": -1}),
        (competitor_from_mapping, CompetitorVideoInput, {"title": "a", "days_old": -1}),
        (
            competitor_from_mapping,
            CompetitorVideoInput,
            {"title": "a", "subscribers": "bad"},
        ),
        (_engagement_from_mapping, SeoEngagementInput, {"views": -1}),
        (_engagement_from_mapping, SeoEngagementInput, {"watch_time_seconds": -1}),
    ],
)
def test_invalid_row_rejected_identically(converter, model, payload: dict) -> None:
    with pytest.raises(ValidationError) as mapping_error:
        converter(payload)
    with pytest.raises(ValidationError) as model_error:
        model.model_validate(payload)
    assert mapping_error.value.errors() == model_error.value.errors()


def test_mapping_only_defaults_do_not_relax_required_http_fields() -> None:
    assert arm_from_mapping({}) == seo.AbArm("arm")
    assert competitor_from_mapping({}) == seo.CompetitorVideo("")
    assert _engagement_from_mapping({}) == seo.Engagement()
    with pytest.raises(ValidationError):
        AbArmInput.model_validate({})
    with pytest.raises(ValidationError):
        CompetitorVideoInput.model_validate({})


@pytest.mark.parametrize("endpoint", ["score", "optimize"])
@pytest.mark.parametrize("platform", ["youtube", "youtube_shorts", "tiktok", "all"])
def test_http_service_engine_parity(
    client: TestClient, service: ContentFactoryService, endpoint: str, platform: str
) -> None:
    payload = {
        "title": "History explained",
        "keywords": ["history"],
        "duration_seconds": "30",
        "aspect_ratio": "9:16",
        "watermark": "false",
        "has_captions": "true",
        "caption_source": "manual",
        "engagement": {"views": "100", "completion_rate": "0.8"},
    }
    response = client.post(
        f"/seo/{endpoint}", json={"platform": platform, "pack": payload}
    )
    assert response.status_code == 200
    method = getattr(service, f"seo_{endpoint}")
    assert response.json() == method(platform, payload)
    assert response.json() == method(
        platform, SeoPackInput.model_validate(payload).to_engine()
    )


@pytest.mark.parametrize(
    "payload", [{"watermark": "invalid"}, {"engagement": {"views": -1}}]
)
def test_http_invalid_pack_matches_service(
    client: TestClient, service: ContentFactoryService, payload: dict
) -> None:
    response = client.post("/seo/score", json={"pack": payload})
    assert response.status_code == 422
    with pytest.raises(ValidationError):
        service.seo_score("youtube", payload)


def test_http_ab_and_keyword_parity(
    client: TestClient, service: ContentFactoryService
) -> None:
    arms = [
        {"name": "a", "impressions": "10000", "clicks": "400"},
        {"name": "b", "impressions": "10000", "clicks": "500"},
    ]
    response = client.post("/seo/ab/evaluate", json={"metric": "ctr", "arms": arms})
    assert response.status_code == 200
    assert response.json() == service.seo_ab_evaluate("ctr", arms)
    competitors = [{"title": "History explained", "views": "1000", "days_old": "0"}]
    response = client.post(
        "/seo/keywords", json={"keywords": ["history"], "competitors": competitors}
    )
    assert response.status_code == 200
    assert response.json() == service.seo_keywords(["history"], competitors)


def test_project_engagement_mapping_parity(
    service: ContentFactoryService, sample_project
) -> None:
    payload = {"views": "100", "average_view_seconds": "20", "completion_rate": "0.7"}
    mapped = service.seo_score_project(sample_project.id, engagement=payload)
    typed = service.seo_score_project(
        sample_project.id,
        engagement=SeoEngagementInput.model_validate(payload).to_engine(),
    )
    assert mapped == typed
    with pytest.raises(ValidationError):
        service.seo_score_project(sample_project.id, engagement={"views": -1})
