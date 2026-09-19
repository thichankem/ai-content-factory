"""The production pipeline: render an approved timeline to a video file."""

from __future__ import annotations

import tempfile
from pathlib import Path
from urllib.parse import urlsplit

from .. import timeline
from ..models import Project, ProjectStatus, VideoAsset
from ..render import RenderError, render_video_file
from ..resources import JobKind
from ..store import StoreConflictError
from .errors import NotFoundError, StateConflictError
from .studio import StudioMixin


class ProductionMixin(StudioMixin):
    """Owns the ffmpeg export and the project mutation that records it."""

    def render_video(
        self, project_id: str, export_format: str = "webm", audio_ref: str | None = None
    ) -> Project:
        if export_format not in {"webm", "mp4"}:
            raise ValueError("export_format must be webm or mp4.")
        # A running generation worker rewrites the project on every step, and
        # the compare-and-save at the end of this method rejects an export
        # whose snapshot moved. Since an export is expensive (seconds to
        # minutes of real ffmpeg work), wait for the pipeline to settle first
        # and only then take the snapshot everything is checked against.
        if not self.wait_for_workers(
            self._settings.render_settle_seconds, project_id=project_id
        ):
            raise StateConflictError(
                "The generation pipeline is still running for this project; "
                "retry the render once it finishes."
            )
        project = self.get_project(project_id).model_copy(deep=True)
        snapshot = project.model_copy(deep=True)
        if project.video_project is None:
            raise StateConflictError("No video project yet.")
        if project.status not in (
            ProjectStatus.GENERATING,
            ProjectStatus.VIDEO_REVIEW,
        ):
            raise StateConflictError(
                f"Cannot render video while status is '{project.status.value}'."
            )
        if any(s.trim_end or s.reverse for s in project.video_project.scenes):
            raise RenderError("Local export does not support trim_end or reverse.")
        plan = timeline.compile_render_plan(
            project.video_project,
            project.id,
            narration_urls={
                track.scene_id: track.audio_url
                for track in (project.voiceover.tracks if project.voiceover else [])
            },
        )
        limit = self._settings.render_max_dimension
        if limit and max(plan.width, plan.height) > limit:
            scale = limit / max(plan.width, plan.height)
            plan.width = max(2, int(plan.width * scale) // 2 * 2)
            plan.height = max(2, int(plan.height * scale) // 2 * 2)
            for step in plan.steps:
                step.font_size = max(1, round(step.font_size * scale))
        output_path = (
            Path(self._settings.library_dir)
            / "videos"
            / f"{project.id}.{export_format}"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        audio_path = self._resolve_render_ref(audio_ref) if audio_ref else None
        music_path = None if audio_path else self._music_bed_for(project)
        background = self._background_video_for(project)
        if background is not None:
            background = self._asset_sandbox.resolve(background)
        with tempfile.TemporaryDirectory(
            dir=output_path.parent, prefix=".export-"
        ) as tmp:
            target = Path(tmp) / output_path.name
            # Admission control first: on a laptop this is what stops two heavy
            # jobs (export + transcribe) from fighting for the same 8 GB GPU and
            # the same CPU cores. Threads are trimmed under memory pressure.
            with self._governor.job(JobKind.RENDER):
                render_video_file(
                    plan,
                    target,
                    resolve_media=self._resolve_render_ref,
                    music_path=music_path,
                    background_video=background,
                    export_format=export_format,
                    threads=self._governor.recommended_threads(),
                    audio_path=audio_path,
                    governor=self._governor,
                )
            project.video = VideoAsset(
                asset_url=f"/projects/{project.id}/video",
                thumbnail_url=f"/projects/{project.id}/thumbnail",
                duration_seconds=round(plan.total_seconds),
                format=export_format,
                size_bytes=target.stat().st_size,
            )
            project.progress = 100
            project.error = None
            if project.status == ProjectStatus.GENERATING:
                self._transition(project, ProjectStatus.VIDEO_REVIEW)
            # Compare-and-save under one lock: an editor that lands between
            # the render start and now rejects the export instead of being
            # silently overwritten.
            try:
                self._store.save_if_unchanged(project, snapshot)
            except StoreConflictError as exc:
                # Only a concurrent *editor* can reach this now: the generation
                # worker was waited for above. Say what the caller can do about
                # it instead of only what was lost.
                raise StateConflictError(
                    "Project changed during rendering; export discarded. "
                    "Re-run the render once the other edit has finished."
                ) from exc
            target.replace(output_path)
            return project

    def _resolve_render_ref(self, ref: str) -> Path:
        parsed = urlsplit(ref)
        if parsed.netloc or (parsed.scheme and not Path(ref).is_absolute()):
            raise NotFoundError("Rendering accepts local media only.")
        if ".." in ref.replace("\\", "/").split("/"):
            raise NotFoundError("Invalid local media reference.")
        path = self._resolve_media_url(ref)
        if path is None:
            path = self.resolve_media_ref(ref)
        return self._asset_sandbox.resolve(path)

    def _music_bed_for(self, project: Project) -> Path | None:
        """Return a background-music bed for the project, or None if disabled."""
        video = project.video_project
        if video is None or not video.background_music:
            return None
        if video.background_music_url:
            return self._resolve_render_ref(video.background_music_url)
        music_dir = Path(self._settings.library_dir) / "music"
        music_dir.mkdir(parents=True, exist_ok=True)
        bed = music_dir / f"{project.id}.ogg"
        if not bed.is_file():
            try:
                from ..media import synthesize_music_bed

                synthesize_music_bed(
                    bed, max(8.0, float(project.duration_target_seconds))
                )
            except Exception:  # noqa: BLE001 - no music bed is a valid outcome for a render
                return None
        return bed if bed.is_file() else None
