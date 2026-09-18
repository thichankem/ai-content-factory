"""Universal media library, re-cook pipeline and AI video edits."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, BinaryIO

from .. import media_tools
from ..models import (
    MediaItem,
    MediaKind,
    Project,
    ReCookRequest,
    ReCookResult,
    YouTubeSearchResult,
    YouTubeTranscriptResult,
)
from .errors import (
    NotFoundError,
)
from .voice import VoiceMixin


class MediaMixin(VoiceMixin):
    """Universal media library, re-cook pipeline and AI video edits."""

    # --- Universal Media Library & Content Re-Cook ----------------------------

    def media_upload(
        self, filename: str, content: bytes, language: str = "en"
    ) -> MediaItem:
        """Upload any media file (video/audio/image/document) to the library."""
        return self._media.upload(filename, content, language=language)

    def media_upload_stream(
        self, filename: str, stream: BinaryIO, language: str = "en"
    ) -> MediaItem:
        return self._media.upload_stream(filename, stream, language=language)

    def media_from_url(
        self, url: str, language: str = "vi", extract_audio: bool = False
    ) -> MediaItem:
        """Download an external video or audio by URL into the media library."""
        return self._media.download_from_url(
            url, language=language, extract_audio=extract_audio
        )

    def download_audio_clip(
        self,
        url: str,
        start_seconds: float = 0.0,
        end_seconds: float = 0.0,
        language: str = "vi",
    ) -> MediaItem:
        """Download any audio by URL, optionally cutting a specific clip.

        The audio is always extracted (``extract_audio=True``). When a valid
        ``end_seconds > start_seconds`` range is given, the clip is trimmed to
        that range and registered as its own media item.
        """
        item = self.media_from_url(url, language=language, extract_audio=True)
        if not (end_seconds and end_seconds > start_seconds):
            return item
        source = self._media.path_for(item)
        if source is None:
            return item
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            target = tmp.name
        try:
            media_tools.trim_audio(source, start_seconds, end_seconds, target)
            with Path(target).open("rb") as f:
                return self._media.upload_stream(
                    f"clip_{item.filename}",
                    f,
                    source=f"url:{url}",
                    language=language,
                )
        finally:
            Path(target).unlink(missing_ok=True)

    def search_youtube(self, query: str, limit: int = 8) -> list[YouTubeSearchResult]:
        """Search YouTube for videos matching ``query`` (metadata only)."""
        return self._media.search_youtube(query, limit)

    def youtube_download(
        self,
        url: str,
        language: str = "vi",
        extract_audio: bool = False,
        auto_transcribe: bool = False,
    ) -> MediaItem:
        """Download a YouTube video (by URL or id) into the media library.

        When ``auto_transcribe`` is set, the item is transcribed right away
        (existing subtitles first, then faster-whisper).
        """
        item = self.media_from_url(url, language=language, extract_audio=extract_audio)
        if auto_transcribe:
            item = self.media_transcribe(item.id, language=language)
        return item

    def youtube_transcript(
        self, url: str, language: str = "en"
    ) -> YouTubeTranscriptResult:
        """Get a transcript for a YouTube video by any means.

        Reuses the video's own subtitles when available (instant, no model);
        otherwise downloads the audio and runs faster-whisper locally.
        """
        result = self._media.transcribe_youtube(url, language)
        return YouTubeTranscriptResult(
            url=url,
            source=result["source"],
            text=result["text"],
            segments=result["segments"],
            media_id=result["media_id"],
        )

    def media_list(self) -> list[MediaItem]:
        """List every item in the universal media library."""
        return self._media.list_items()

    def media_query(
        self,
        *,
        kind: str | None = None,
        tag: str | None = None,
        q: str | None = None,
        source: str | None = None,
        min_duration: float | None = None,
        max_duration: float | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        sort: str = "newest",
    ) -> list[MediaItem]:
        """Query the media database with rich filters."""
        return self._media.query(
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

    def media_stats(self) -> dict[str, Any]:
        """Aggregate counts and sizes across the library."""
        return self._media.stats()

    def media_all_tags(self) -> list[str]:
        """Every distinct tag across the library."""
        return self._media.all_tags()

    def media_set_tags(self, media_id: str, tags: list[str]) -> MediaItem:
        """Replace an item's tags."""
        return self._media.set_tags(media_id, tags)

    def media_add_tag(self, media_id: str, tag: str) -> MediaItem:
        """Add one tag to an item (idempotent)."""
        return self._media.add_tag(media_id, tag)

    def media_remove_tag(self, media_id: str, tag: str) -> MediaItem:
        """Remove one tag from an item (idempotent)."""
        return self._media.remove_tag(media_id, tag)

    def media_get(self, media_id: str) -> MediaItem:
        """Fetch one media item, raising NotFoundError if absent."""
        try:
            return self._media.require(media_id)
        except KeyError as exc:
            raise NotFoundError(str(exc)) from exc

    def media_delete(self, media_id: str) -> bool:
        """Delete a media item and its backing file."""
        if not self._media.delete(media_id):
            raise NotFoundError(f"media item '{media_id}' not found")
        return True

    def media_transcribe(self, media_id: str, language: str = "en") -> MediaItem:
        """Transcribe a video/audio item so an AI agent can read it."""
        try:
            return self._media.transcribe(media_id, language=language)
        except KeyError as exc:
            raise NotFoundError(str(exc)) from exc

    def media_extract_text(self, media_id: str) -> MediaItem:
        """Extract plain text from a document item."""
        try:
            return self._media.extract_text(media_id)
        except KeyError as exc:
            raise NotFoundError(str(exc)) from exc

    def media_convert(self, media_id: str, target_format: str) -> MediaItem:
        """Convert a media item to another format (mp4/webm/mp3/wav/png/jpg)."""
        try:
            return self._media.convert(media_id, target_format)
        except KeyError as exc:
            raise NotFoundError(str(exc)) from exc
        except FileNotFoundError as exc:
            raise NotFoundError(str(exc)) from exc

    def media_path(self, media_id: str) -> Path | None:
        """Absolute path of a media item's backing file, if present."""
        try:
            item = self._media.require(media_id)
        except KeyError:
            return None
        return self._media.path_for(item)

    def ai_edit_video(
        self,
        video_path: Path,
        image_path: Path,
        output_path: Path,
        *,
        use_vision: bool = False,
    ) -> dict:
        """Run the AI video editor: analyse, place, track, composite, cut, export.

        Returns a JSON-serialisable report describing where/when the image was
        inserted and how much was cut.
        """
        from ..ai_video_editor import AiVideoEditor, _demo_vision_planner

        vision = _demo_vision_planner if use_vision else None
        editor = AiVideoEditor(vision=vision)
        report = editor.edit(video_path, image_path, output_path)
        return {
            "planner": report.planner,
            "source_frames": report.source_frames,
            "output_frames": report.output_frames,
            "fps": report.fps,
            "placement": (
                {
                    "x": report.placement.x,
                    "y": report.placement.y,
                    "w": report.placement.w,
                    "h": report.placement.h,
                    "start_frame": report.placement.start_frame,
                    "end_frame": report.placement.end_frame,
                    "reason": report.placement.reason,
                }
                if report.placement
                else None
            ),
            "cuts": [{"start": c.start, "end": c.end} for c in report.cuts],
            "output_path": report.output_path,
        }

    def recook(self, media_id: str, request: ReCookRequest) -> ReCookResult:
        """Re-cook a source media item into a brand-new project + script."""
        try:
            return self._recook.run(media_id, request, self._store)
        except KeyError as exc:
            raise NotFoundError(str(exc)) from exc

    def _resolve_media_url(self, url: str) -> Path | None:
        """Map a media URL to a local file for the renderer.

        Handles voiceover clips, media-library items, and static uploads so the
        renderer can composite real footage and mix the narration.
        """
        if not url:
            return None
        # Voiceover clip: /projects/{pid}/voiceover/{scene_id}
        parts = url.strip("/").split("/")
        if len(parts) >= 4 and parts[0] == "projects" and parts[2] == "voiceover":
            return self.voiceover_path(parts[1], parts[3])
        # Source-footage frame: /projects/{pid}/frame/{idx}
        if len(parts) >= 4 and parts[0] == "projects" and parts[2] == "frame":
            candidate = (
                Path(self._settings.library_dir)
                / "videos"
                / parts[1]
                / "frames"
                / f"scene_{parts[3]}.jpg"
            )
            return candidate if candidate.is_file() else None
        # Media-library item: /media/{id}/download
        if len(parts) >= 2 and parts[0] == "media":
            try:
                item = self._media.require(parts[1])
            except KeyError:
                return None
            return self._media.path_for(item)
        # Static upload: /uploads/{relpath}
        if parts[0] == "uploads":
            candidate = Path("storage/uploads") / "/".join(parts[1:])
            return candidate if candidate.is_file() else None
        return None

    def _background_video_for(self, project: Project) -> Path | None:
        """Return the source video to use as a moving backdrop, if any."""
        if not project.source_media_id:
            return None
        try:
            item = self._media.require(project.source_media_id)
        except KeyError:
            return None
        if item.kind != MediaKind.VIDEO:
            return None
        return self._media.path_for(item)
