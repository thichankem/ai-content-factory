"""YouTube search & download tests.

Covers the two new capabilities:

* ``GET /youtube/search`` — search YouTube for videos by query (metadata only),
  backed by yt-dlp's ``ytsearch`` extractor.
* ``POST /youtube/download`` — download a YouTube video (by URL or id) into the
  media library, reusing the existing ``download_from_url`` path.

Also verifies the ``youtube_search`` / ``youtube_download`` agent tools (which
are what the MCP server's ``factory_call_tool`` dispatches).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from content_factory import agent_tools
from content_factory.media import MediaLibrary
from content_factory.models import MediaItem, MediaKind


def _fake_ytdl(info: dict) -> MagicMock:
    """A fake ``yt_dlp.YoutubeDL`` whose ``extract_info`` returns ``info``."""
    ydl = MagicMock()
    ydl.extract_info.return_value = info
    ydl.__enter__.return_value = ydl
    ydl.__exit__.return_value = False
    return ydl


_SAMPLE_INFO = {
    "entries": [
        {
            "id": "abc123",
            "title": "Morning Light in Cities",
            "webpage_url": "https://www.youtube.com/watch?v=abc123",
            "duration": 720,
            "channel": "Urban Docs",
            "thumbnail": "https://img.example/abc123.jpg",
            "description": "How low sun shapes streets.",
            "view_count": 1000,
        },
        {"id": "def456", "title": "Another Video"},
    ]
}


# --- Service: search ----------------------------------------------------------


def test_search_youtube_returns_results(service) -> None:
    with patch("yt_dlp.YoutubeDL", return_value=_fake_ytdl(_SAMPLE_INFO)):
        results = service.search_youtube("morning light", limit=2)
    assert len(results) == 2
    first = results[0]
    assert first.id == "abc123"
    assert first.title == "Morning Light in Cities"
    assert first.url == "https://www.youtube.com/watch?v=abc123"
    assert first.duration_seconds == 720
    assert first.uploader == "Urban Docs"
    assert first.view_count == 1000


def test_search_youtube_handles_missing_fields(service) -> None:
    info = {"entries": [{"id": "x1"}]}
    with patch("yt_dlp.YoutubeDL", return_value=_fake_ytdl(info)):
        results = service.search_youtube("q", limit=1)
    assert len(results) == 1
    assert results[0].id == "x1"
    assert results[0].url == "https://www.youtube.com/watch?v=x1"
    assert results[0].title == ""


# --- Service: download --------------------------------------------------------


def test_youtube_download_returns_media_item(service) -> None:
    item = MediaItem(id="m1", filename="vid.mp4", kind=MediaKind.VIDEO)
    with patch.object(service, "media_from_url", return_value=item) as mock:
        result = service.youtube_download("https://www.youtube.com/watch?v=abc123")
    assert result.id == "m1"
    mock.assert_called_once_with(
        "https://www.youtube.com/watch?v=abc123", language="vi", extract_audio=False
    )


def test_youtube_download_auto_transcribes(service) -> None:
    item = MediaItem(id="m1", filename="vid.mp4", kind=MediaKind.VIDEO)
    item.transcription = "auto captions"
    with patch.object(service, "media_from_url", return_value=item) as dl:
        with patch.object(service, "media_transcribe", return_value=item) as tr:
            result = service.youtube_download(
                "https://youtu.be/abc", language="en", auto_transcribe=True
            )
    assert result.transcription == "auto captions"
    dl.assert_called_once_with(
        "https://youtu.be/abc", language="en", extract_audio=False
    )
    tr.assert_called_once_with("m1", language="en")


def test_download_audio_clip_full_audio(service) -> None:
    """Without a range, download_audio_clip just ingests the audio."""
    item = MediaItem(id="m1", filename="a.mp3", kind=MediaKind.AUDIO)
    with patch.object(service, "media_from_url", return_value=item) as dl:
        result = service.download_audio_clip("https://example.com/a.mp3", language="vi")
    assert result.id == "m1"
    dl.assert_called_once_with(
        "https://example.com/a.mp3", language="vi", extract_audio=True
    )


def test_download_audio_clip_trims_range(service, tmp_path) -> None:
    """A valid start/end range trims the downloaded audio into a new clip item."""
    item = MediaItem(id="m1", filename="a.mp3", kind=MediaKind.AUDIO)
    clip = MediaItem(id="clip1", filename="clip_a.mp3", kind=MediaKind.AUDIO)
    source = tmp_path / "a.mp3"
    source.write_bytes(b"\xff\xfb\x90\x64" * 100)
    with patch.object(service, "media_from_url", return_value=item):
        with patch.object(service._media, "path_for", return_value=source):
            with patch.object(service._media, "upload_stream", return_value=clip) as up:
                with patch("content_factory.media_tools.trim_audio") as trim:
                    result = service.download_audio_clip(
                        "https://example.com/a.mp3", start_seconds=1.0, end_seconds=3.0
                    )
    assert result.id == "clip1"
    trim.assert_called_once()
    up.assert_called_once()


# --- API ----------------------------------------------------------------------


def test_api_youtube_search(client: TestClient) -> None:
    with patch("yt_dlp.YoutubeDL", return_value=_fake_ytdl(_SAMPLE_INFO)):
        resp = client.get("/youtube/search", params={"q": "morning light", "limit": 2})
    assert resp.status_code == 200
    body = resp.json()
    assert body["query"] == "morning light"
    assert body["count"] == 2
    assert body["results"][0]["id"] == "abc123"


def test_api_youtube_search_validates_empty_query(client: TestClient) -> None:
    resp = client.get("/youtube/search", params={"q": ""})
    assert resp.status_code == 422


def test_api_youtube_download(client: TestClient) -> None:
    item = MediaItem(id="m1", filename="vid.mp4", kind=MediaKind.VIDEO)
    with patch.object(MediaLibrary, "download_from_url", return_value=item):
        resp = client.post(
            "/youtube/download",
            json={"url": "https://www.youtube.com/watch?v=abc123"},
        )
    assert resp.status_code == 201
    assert resp.json()["id"] == "m1"


# --- Agent tools (MCP dispatch path) ------------------------------------------


def test_agent_youtube_search(service) -> None:
    with patch("yt_dlp.YoutubeDL", return_value=_fake_ytdl(_SAMPLE_INFO)):
        result = agent_tools.dispatch_tool(
            service, "youtube_search", {"query": "morning light", "limit": 2}
        )
    assert len(result) == 2
    assert result[0]["id"] == "abc123"


def test_agent_youtube_download(service) -> None:
    item = MediaItem(id="m1", filename="v.mp4", kind=MediaKind.VIDEO)
    with patch.object(service, "media_from_url", return_value=item):
        result = agent_tools.dispatch_tool(
            service,
            "youtube_download",
            {"url": "https://www.youtube.com/watch?v=abc123"},
        )
    assert result["id"] == "m1"


def test_agent_youtube_search_requires_query(service) -> None:
    with pytest.raises(agent_tools.ToolError):
        agent_tools.dispatch_tool(service, "youtube_search", {})


# --- Transcript by any means ---------------------------------------------------


def test_vtt_to_text_strips_timestamps_and_tags() -> None:
    vtt = (
        "WEBVTT\n\n"
        "00:00:00.000 --> 00:00:03.000 align:start position:0%\n"
        "<c>Morning light</c> changes how cities feel.\n\n"
        "00:00:03.000 --> 00:00:06.000\n"
        "Low sun casts long shadows.\n"
    )
    text = MediaLibrary._vtt_to_text(vtt)
    assert "Morning light changes how cities feel." in text
    assert "Low sun casts long shadows." in text
    assert "-->" not in text


def test_youtube_transcript_uses_subtitles_when_available(service) -> None:
    with patch.object(
        service._media, "fetch_subtitles", return_value="Morning light shapes cities."
    ) as mock:
        result = service.youtube_transcript("https://youtu.be/abc", language="en")
    assert result.source == "subtitles"
    assert "Morning light" in result.text
    assert result.media_id is None
    mock.assert_called_once_with("https://youtu.be/abc", "en")


def test_youtube_transcript_falls_back_to_whisper(service) -> None:
    item = MediaItem(id="m1", filename="a.webm", kind=MediaKind.VIDEO)
    item.transcription = "spoken words from whisper"
    with patch.object(service._media, "fetch_subtitles", return_value=None):
        with patch.object(service._media, "download_from_url", return_value=item):
            with patch.object(service._media, "transcribe", return_value=item):
                result = service.youtube_transcript("https://youtu.be/abc", "en")
    assert result.source == "whisper"
    assert result.media_id == "m1"


def test_transcribe_reuses_youtube_subtitles(service) -> None:
    """A downloaded YouTube item is transcribed from its own captions, no model."""
    item = MediaItem(
        id="m1",
        filename="v.webm",
        kind=MediaKind.VIDEO,
        source="url:https://www.youtube.com/watch?v=abc",
    )
    service._media.add_item(item)
    with patch.object(
        service._media, "fetch_subtitles", return_value="Auto captions text."
    ) as mock:
        result = service._media.transcribe("m1", "en")
    assert result.transcription == "Auto captions text."
    mock.assert_called_once()


def test_api_youtube_transcript(client: TestClient) -> None:
    with patch.object(
        MediaLibrary, "fetch_subtitles", return_value="Morning light shapes cities."
    ):
        resp = client.post(
            "/youtube/transcript",
            json={"url": "https://youtu.be/abc", "language": "en"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "subtitles"
    assert "Morning light" in body["text"]


def test_agent_youtube_transcript(service) -> None:
    with patch.object(
        service._media, "fetch_subtitles", return_value="Some transcript text."
    ):
        result = agent_tools.dispatch_tool(
            service,
            "youtube_transcript",
            {"url": "https://youtu.be/abc", "language": "en"},
        )
    assert result["source"] == "subtitles"
    assert result["text"]
