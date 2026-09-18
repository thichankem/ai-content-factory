"""Universal media library, re-cook pipeline and AI video edits."""

from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

from ..models import MediaItem, MediaKind, Project, ReCookRequest, ReCookResult
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

    def media_list(self) -> list[MediaItem]:
        """List every item in the universal media library."""
        return self._media.list()

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
