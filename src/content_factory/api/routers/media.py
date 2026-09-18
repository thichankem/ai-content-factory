"""Universal media library and AI video editor endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import FileResponse

from ...media import UploadTooLargeError
from ...models import (
    AudioClipRequest,
    MediaIngestUrlRequest,
    MediaItem,
    ReCookRequest,
    ReCookResult,
    YouTubeDownloadRequest,
    YouTubeSearchResponse,
    YouTubeTranscriptRequest,
    YouTubeTranscriptResult,
)
from ...service import ContentFactoryService, NotFoundError
from ..deps import guard_value


def build_router(service: ContentFactoryService) -> APIRouter:

    router = APIRouter()

    @router.post("/media/upload", response_model=MediaItem, status_code=201)
    def media_upload(
        file: UploadFile = File(...),  # noqa: B008
        language: str = Form("en"),
    ) -> MediaItem:
        """Upload any media file (video/audio/image/document) to the library."""
        try:
            return service.media_upload_stream(
                file.filename or "upload", file.file, language
            )
        except UploadTooLargeError as exc:
            raise HTTPException(status_code=413, detail=str(exc)) from exc

    @router.post("/media/from-url", response_model=MediaItem, status_code=201)
    def media_from_url(payload: MediaIngestUrlRequest) -> MediaItem:
        """Ingest an external video or audio from a URL (YouTube/TikTok/direct link)."""
        return guard_value(
            lambda: service.media_from_url(
                payload.url,
                language=payload.language,
                extract_audio=payload.extract_audio,
            )
        )

    @router.post("/media/audio-clip", response_model=MediaItem, status_code=201)
    def media_audio_clip(payload: AudioClipRequest) -> MediaItem:
        """Download any audio by URL, optionally cutting a specific clip range."""
        return guard_value(
            lambda: service.download_audio_clip(
                payload.url,
                start_seconds=payload.start_seconds,
                end_seconds=payload.end_seconds,
                language=payload.language,
            )
        )

    @router.get("/youtube/search", response_model=YouTubeSearchResponse)
    def youtube_search(
        q: str = Query(..., min_length=1, max_length=200),
        limit: int = Query(8, ge=1, le=25),
    ) -> YouTubeSearchResponse:
        """Search YouTube for videos matching ``q`` (metadata only)."""
        results = service.search_youtube(q, limit)
        return YouTubeSearchResponse(query=q, count=len(results), results=results)

    @router.post("/youtube/download", response_model=MediaItem, status_code=201)
    def youtube_download(payload: YouTubeDownloadRequest) -> MediaItem:
        """Download a YouTube video (by URL or id) into the media library."""
        return guard_value(
            lambda: service.youtube_download(
                payload.url,
                language=payload.language,
                extract_audio=payload.extract_audio,
                auto_transcribe=payload.auto_transcribe,
            )
        )

    @router.post("/youtube/transcript", response_model=YouTubeTranscriptResult)
    def youtube_transcript(
        payload: YouTubeTranscriptRequest,
    ) -> YouTubeTranscriptResult:
        """Get a transcript for a YouTube video by any means.

        Reuses the video's own subtitles when available (instant, no model);
        otherwise downloads the audio and runs faster-whisper locally.
        """
        return guard_value(
            lambda: service.youtube_transcript(payload.url, payload.language)
        )

    @router.post("/ai-editor/edit")
    async def ai_editor_edit(
        video: UploadFile = File(...),  # noqa: B008
        image: UploadFile = File(...),  # noqa: B008
        use_vision: bool = Form(False),
    ) -> dict:
        """AI Video Editor: analyse a video, composite an image naturally, cut.

        Accepts a ``video`` and an ``image`` (multipart). The pipeline analyses
        the video, picks a natural placement (heuristic, or a vision planner when
        ``use_vision`` is true), tracks it across frames, composites with a
        feathered mask, trims dead air, and exports ``final.mp4``. Returns a
        report plus a download URL for the edited video.
        """
        import tempfile
        import uuid

        video_bytes = await video.read()
        image_bytes = await image.read()
        if not video_bytes or not image_bytes:
            raise HTTPException(
                status_code=422, detail="Both video and image are required."
            )
        tmp = Path(tempfile.gettempdir()) / f"cf-ai-edit-{uuid.uuid4().hex}"
        tmp.mkdir(parents=True, exist_ok=True)
        video_path = tmp / f"video{video.filename or '.mp4'}"
        image_path = tmp / f"image{image.filename or '.png'}"
        video_path.write_bytes(video_bytes)
        image_path.write_bytes(image_bytes)
        out_dir = Path("library/videos")
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = out_dir / f"ai-edit-{uuid.uuid4().hex[:12]}.mp4"
        try:
            report = service.ai_edit_video(
                video_path, image_path, output_path, use_vision=use_vision
            )
        finally:
            try:
                for p in (video_path, image_path):
                    if p.exists():
                        p.unlink()
                tmp.rmdir()
            except OSError:
                pass
        report["download_url"] = f"/ai-editor/output/{output_path.name}"
        return report

    @router.get("/ai-editor/output/{filename}")
    def ai_editor_output(filename: str) -> FileResponse:
        """Serve an edited video produced by the AI editor."""
        path = Path("library/videos") / filename
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Edited video not found.")
        return FileResponse(path, media_type="video/mp4")

    @router.get("/media", response_model=list[MediaItem])
    def media_list(
        kind: str | None = Query(None, description="video|audio|image|document"),
        tag: str | None = Query(None, description="Filter by a tag"),
        q: str | None = Query(None, description="Free-text over name/transcript/tags"),
        source: str | None = Query(None, description="Filter by source"),
        min_duration: float | None = Query(None, ge=0),
        max_duration: float | None = Query(None, ge=0),
        date_from: str | None = Query(None, description="ISO date, inclusive"),
        date_to: str | None = Query(None, description="ISO date, inclusive"),
        sort: str = Query("newest", description="newest|oldest|name|size|duration"),
    ) -> list[MediaItem]:
        """Query the media database with rich filters."""
        return service.media_query(
            kind=kind,
            tag=tag,
            q=q,
            source=source,
            min_duration=min_duration,
            max_duration=max_duration,
            date_from=date_from,
            date_to=date_to,
            sort=sort,
        )

    @router.get("/media/stats")
    def media_stats() -> dict[str, Any]:
        """Aggregate counts and sizes across the library."""
        return service.media_stats()

    @router.get("/media/tags")
    def media_tags() -> list[str]:
        """Every distinct tag across the library."""
        return service.media_all_tags()

    @router.post("/media/{media_id}/tags", response_model=MediaItem)
    def media_set_tags(media_id: str, tags: list[str]) -> MediaItem:
        """Replace an item's tags."""
        return guard_value(lambda: service.media_set_tags(media_id, tags))

    @router.post("/media/{media_id}/tags/{tag}", response_model=MediaItem)
    def media_add_tag(media_id: str, tag: str) -> MediaItem:
        """Add one tag to an item (idempotent)."""
        return guard_value(lambda: service.media_add_tag(media_id, tag))

    @router.delete("/media/{media_id}/tags/{tag}", response_model=MediaItem)
    def media_remove_tag(media_id: str, tag: str) -> MediaItem:
        """Remove one tag from an item (idempotent)."""
        return guard_value(lambda: service.media_remove_tag(media_id, tag))
        return service.media_list()

    @router.get("/media/{media_id}", response_model=MediaItem)
    def media_get(media_id: str) -> MediaItem:
        """Fetch one media item with its metadata and AI reading."""
        return guard_value(lambda: service.media_get(media_id))

    @router.get("/media/{media_id}/download")
    def media_download(media_id: str) -> FileResponse:
        """Serve the raw media file."""
        path = service.media_path(media_id)
        if path is None:
            raise HTTPException(status_code=404, detail="Media file not found")
        return FileResponse(path)

    @router.delete("/media/{media_id}")
    def media_delete(media_id: str) -> dict[str, bool]:
        """Delete a media item and its backing file."""
        guard_value(lambda: service.media_delete(media_id))
        return {"deleted": True}

    @router.post("/media/{media_id}/transcribe", response_model=MediaItem)
    def media_transcribe(media_id: str, language: str = "en") -> MediaItem:
        """Transcribe a video/audio item so an AI agent can read it."""
        return guard_value(lambda: service.media_transcribe(media_id, language))

    @router.post("/media/{media_id}/extract-text", response_model=MediaItem)
    def media_extract_text(media_id: str) -> MediaItem:
        """Extract plain text from a document item."""
        return guard_value(lambda: service.media_extract_text(media_id))

    @router.post("/media/{media_id}/recook", response_model=ReCookResult)
    def media_recook(media_id: str, payload: ReCookRequest) -> ReCookResult:
        """Re-cook a source media item into a brand-new project + script."""
        return guard_value(lambda: service.recook(media_id, payload))

    @router.post("/media/{media_id}/convert", response_model=MediaItem)
    def media_convert(media_id: str, target_format: str = "mp4") -> MediaItem:
        """Convert a media item to another format (mp4/webm/mp3/wav/png/jpg).

        The original is preserved; a new sibling MediaItem is created.
        """
        try:
            return service.media_convert(media_id, target_format)
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    return router
