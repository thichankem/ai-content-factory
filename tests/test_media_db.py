"""Media database tests: rich query, tags, and aggregate stats."""

from __future__ import annotations

from content_factory.models import MediaItem


def _seed(service) -> list[MediaItem]:
    audio = service.media_upload("voice.mp3", b"\xff\xfb\x90\x64" * 100, language="en")
    image = service.media_upload("thumb.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)
    video = service.media_upload("clip.mp4", b"\x00" * 200, language="en")
    service.media_set_tags(audio.id, ["voice", "demo"])
    service.media_set_tags(image.id, ["thumbnail", "demo"])
    return [audio, image, video]


def test_query_by_kind(service) -> None:
    _seed(service)
    assert len(service.media_query(kind="audio")) == 1
    assert len(service.media_query(kind="image")) == 1
    assert len(service.media_query(kind="video")) == 1


def test_query_by_tag(service) -> None:
    _seed(service)
    assert len(service.media_query(tag="voice")) == 1
    assert len(service.media_query(tag="demo")) == 2
    assert len(service.media_query(tag="missing")) == 0


def test_query_free_text(service) -> None:
    _seed(service)
    assert len(service.media_query(q="voice")) == 1
    assert len(service.media_query(q="thumb")) == 1
    assert len(service.media_query(q="nothing-here")) == 0


def test_query_sort(service) -> None:
    _seed(service)
    newest = service.media_query(sort="newest")
    oldest = service.media_query(sort="oldest")
    assert newest[0].created_at >= newest[-1].created_at
    assert oldest[0].created_at <= oldest[-1].created_at


def test_tags_crud(service) -> None:
    item = service.media_upload("a.mp3", b"\xff\xfb\x90\x64" * 10)
    updated = service.media_set_tags(item.id, ["voice", "Voice", "  demo  "])
    assert updated.tags == ["voice", "demo"]  # normalised + de-duped
    added = service.media_add_tag(item.id, "important")
    assert "important" in added.tags
    removed = service.media_remove_tag(item.id, "important")
    assert "important" not in removed.tags


def test_all_tags(service) -> None:
    _seed(service)
    assert "voice" in service.media_all_tags()
    assert "thumbnail" in service.media_all_tags()


def test_stats(service) -> None:
    _seed(service)
    stats = service.media_stats()
    assert stats["total_items"] >= 3
    assert stats["by_kind"]["audio"] >= 1
    assert stats["by_kind"]["image"] >= 1
    assert stats["total_bytes"] > 0


def test_api_query_and_stats(client) -> None:
    resp = client.get("/media", params={"kind": "audio"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    stats = client.get("/media/stats")
    assert stats.status_code == 200
    assert "by_kind" in stats.json()
    tags = client.get("/media/tags")
    assert tags.status_code == 200
    assert isinstance(tags.json(), list)


def test_api_tags_endpoints(client) -> None:
    # Upload a tiny image and tag it via the API.
    up = client.post(
        "/media/upload",
        files={"file": ("t.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 30, "image/png")},
    )
    mid = up.json()["id"]
    r = client.post(f"/media/{mid}/tags", json=["demo"])
    assert r.status_code == 200
    assert r.json()["tags"] == ["demo"]
    r2 = client.post(f"/media/{mid}/tags/extra")
    assert "extra" in r2.json()["tags"]
    r3 = client.delete(f"/media/{mid}/tags/extra")
    assert "extra" not in r3.json()["tags"]
