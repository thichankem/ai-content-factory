"""Automated tests for history, disaster niche, and commercial editing features."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from content_factory.api import create_app
from content_factory.config import Settings
from content_factory.map_generator import (
    generate_infographic_svg,
    generate_route_map_svg,
)
from content_factory.models import (
    InfographicSpec,
    MapRoutePoint,
    MapRouteSpec,
    ResearchSource,
)
from content_factory.on_this_day import (
    get_events_for_date,
    get_events_for_today,
    search_historical_events,
)
from content_factory.research import extract_structured_timeline, reconcile_facts
from content_factory.sensitivity import audit_sensitivity


@pytest.fixture
def client(tmp_path) -> TestClient:
    settings = Settings(
        store_path=str(tmp_path / "projects.json"),
        uploads_dir=str(tmp_path / "uploads"),
    )
    app = create_app(settings)
    return TestClient(app)


def test_extract_structured_timeline():
    text = (
        "1912-04-14 23:40: Tàu Titanic va chạm tảng băng trôi khổng lồ.\n"
        "1912-04-15 00:05: Nước tràn vào 5 khoang kín nước, bắt đầu chìm.\n"
        "1912-04-15 02:20: Con tàu gãy đôi và chìm xuống đáy đại dương, "
        "khiến 1517 người thiệt mạng."
    )
    timeline = extract_structured_timeline(text, topic="Thảm họa Titanic")
    assert len(timeline.events) >= 2
    assert timeline.total_casualties == 1517
    assert timeline.climax_event_index is not None
    climax_event = timeline.events[timeline.climax_event_index]
    assert climax_event.is_climax is True


def test_reconcile_facts_single_and_multiple_sources():
    # Single consensus source -> Verified
    src1 = ResearchSource(
        id="s1",
        title="Titanic Inquiry 1912",
        url="https://example.com/1",
        source_type="report",
        summary="Thống kê ghi nhận 1517 người chết trong vụ đắm tàu.",
        highlights=["1517 nạn nhân"],
    )
    src2 = ResearchSource(
        id="s2",
        title="British Board of Trade",
        url="https://example.com/2",
        source_type="archive",
        summary="Xác nhận 1517 người thiệt mạng trong thảm họa Titanic.",
        highlights=[],
    )
    report = reconcile_facts(sources=[src1, src2])
    assert report.verified_count >= 1
    assert report.disputed_count == 0
    assert report.overall_confidence == "verified"


def test_reconcile_facts_discrepancy():
    # Disputed casualty count across sources
    src1 = ResearchSource(
        id="s1",
        title="Nguồn A",
        url="https://example.com/a",
        source_type="news",
        summary="Khoảng 1490 người chết.",
        highlights=[],
    )
    src2 = ResearchSource(
        id="s2",
        title="Nguồn B",
        url="https://example.com/b",
        source_type="news",
        summary="Con số chính xác là 1517 người chết.",
        highlights=[],
    )
    report = reconcile_facts(sources=[src1, src2])
    assert report.disputed_count >= 1
    assert report.overall_confidence == "disputed"


def test_audit_sensitivity_clean():
    text = (
        "Vào đêm 14 tháng 4 năm 1912, con tàu Titanic đã va phải một tảng băng trôi. "
        "Các thủy thủ đã phát tín hiệu cấp cứu và di tản hành khách lên "
        "thuyền cứu sinh. "
        "Đây là một bài học sâu sắc cho ngành hàng hải quốc tế."
    )
    report = audit_sensitivity(text, topic="Titanic")
    assert report.safety_score >= 90
    assert report.is_safe_for_monetization is True
    assert report.disclaimer_required is False


def test_audit_sensitivity_violations():
    text = (
        "Xác người la liệt kinh hoàng đẫm máu trôi dạt khắp mặt biển. "
        "Nhiều giả thuyết chắc chắn rằng đây là âm mưu bị chính phủ che giấu "
        "để trừ khử các nhà tài phiệt phản đối thành lập FED."
    )
    report = audit_sensitivity(text, topic="Titanic", casualties=1517)
    assert report.safety_score < 70
    assert len(report.findings) >= 2
    assert report.disclaimer_required is True
    assert report.recommended_disclaimer is not None


def test_generate_route_map_svg():
    spec = MapRouteSpec(
        title="Hải trình Titanic",
        map_type="nautical",
        points=[
            MapRoutePoint(label="Southampton", x=10.0, y=20.0),
            MapRoutePoint(label="Point of Sinking", x=70.0, y=50.0),
        ],
        show_danger_zone=True,
        danger_label="Vị trí chìm",
        danger_x=70.0,
        danger_y=50.0,
    )
    svg = generate_route_map_svg(spec)
    assert "<svg" in svg
    assert "Hải trình Titanic" in svg
    assert "Southampton" in svg
    assert "Vị trí chìm" in svg


def test_generate_infographic_svg():
    spec = InfographicSpec(
        title="So sánh thương vong hàng hải",
        subtitle="Số liệu ước tính",
        labels=["Titanic", "Lusitania"],
        values=[1517, 1198],
        unit="người",
    )
    svg = generate_infographic_svg(spec)
    assert "<svg" in svg
    assert "So sánh thương vong hàng hải" in svg
    assert "Titanic" in svg
    assert "Lusitania" in svg


def test_on_this_day_queries():
    # Titanic on April 14
    events_april_14 = get_events_for_date(4, 14)
    assert any("Titanic" in ev.title for ev in events_april_14)

    # Search keyword
    mh370_results = search_historical_events("MH370")
    assert len(mh370_results) >= 1
    assert "MH370" in mh370_results[0].title

    # Today events fallback
    today_events = get_events_for_today()
    assert len(today_events) >= 1


def test_history_and_disaster_api_endpoints(client):
    # 1. On this day endpoint
    resp = client.get("/history/on-this-day?month=4&day=14")
    assert resp.status_code == 200
    data = resp.json()
    assert any("Titanic" in item["title"] for item in data)

    # 2. Search history endpoint
    resp = client.get("/history/search?q=Chornobyl")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

    # 3. Create project
    proj_resp = client.post(
        "/projects",
        json={
            "name": "Chornobyl 1986",
            "topic": (
                "Thảm họa lò phản ứng số 4 nổ tung khiến hàng ngàn người phơi nhiễm"
            ),
            "target_language": "vi",
            "duration_target_seconds": 60,
            "script_style": "disaster-retelling",
        },
    )
    assert proj_resp.status_code == 201
    pid = proj_resp.json()["id"]

    # 4. Extract timeline
    tl_resp = client.post(f"/projects/{pid}/timeline/extract")
    assert tl_resp.status_code == 200
    assert len(tl_resp.json()["events"]) >= 1

    # 5. Reconcile facts
    fact_resp = client.post(
        f"/projects/{pid}/facts/reconcile",
        json={"claims": []},
    )
    assert fact_resp.status_code == 200

    # 6. Sensitivity audit
    sens_resp = client.post(f"/projects/{pid}/sensitivity/audit")
    assert sens_resp.status_code == 200
    assert "safety_score" in sens_resp.json()

    # 7. Generate procedural map
    map_resp = client.post(
        f"/projects/{pid}/graphics/map",
        json={
            "title": "Chornobyl Exclusion Zone",
            "map_type": "disaster",
            "points": [{"label": "Pripyat", "x": 50.0, "y": 50.0}],
            "show_danger_zone": True,
            "danger_label": "Lò phản ứng số 4",
            "danger_x": 50.0,
            "danger_y": 50.0,
        },
    )
    assert map_resp.status_code == 200
    assert map_resp.headers["content-type"] == "image/svg+xml"
    assert "<svg" in map_resp.text

    # 8. Generate procedural infographic
    info_resp = client.post(
        f"/projects/{pid}/graphics/infographic",
        json={
            "title": "So sánh mức phóng xạ",
            "labels": ["Mức an toàn", "Chornobyl"],
            "values": [1.0, 400.0],
            "unit": "lần",
        },
    )
    assert info_resp.status_code == 200
    assert info_resp.headers["content-type"] == "image/svg+xml"
    assert "<svg" in info_resp.text
