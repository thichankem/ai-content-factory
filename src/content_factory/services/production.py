"""Image/voice post-production studio and the ffmpeg renderer."""

from __future__ import annotations

import tempfile
from pathlib import Path
from urllib.parse import urlsplit

from .. import timeline
from ..image_voice_service import IMAGE_PRESETS, VOICE_PRESETS_DOC
from ..models import Project, ProjectStatus, VideoAsset
from ..render import RenderError, render_video_file
from ..resources import JobKind
from ..store import StoreConflictError
from .errors import (
    NotFoundError,
    StateConflictError,
)
from .media_tools import MediaToolsMixin


class ProductionMixin(MediaToolsMixin):
    """Image/voice post-production studio and the ffmpeg renderer."""

    # --- Image & voice studio (Photoshop / Audition style) ---------------------

    def edit_image(
        self,
        data: bytes,
        *,
        ops: list[dict] | None = None,
        preset: str | None = None,
        export_format: str = "png",
    ) -> dict:
        """Edit an image with an op pipeline or a named look; persist the result."""
        return self._studio.edit_image_bytes(
            data, ops=ops, preset=preset, export_format=export_format
        )

    # --- image analysis & accessibility --------------------------------------

    def analyze_image(self, data: bytes) -> dict:
        """Describe an image from its pixel statistics (vision-free)."""
        return self._studio.analyze_image_bytes(data)

    def image_op_catalog(self) -> dict:
        """Full op catalogue grouped by category, with plain-language docs."""
        return self._studio.image_op_catalog()

    def describe_image_op(self, name: str, params: dict | None = None) -> dict:
        """Explain a single op in plain language."""
        return self._studio.describe_image_op(name, params)

    def suggest_image_edits(self, data: bytes) -> dict:
        """Histogram-based auto-suggestions for an image."""
        return self._studio.suggest_image_edits(data)

    def batch_edit_image(
        self,
        images: list[bytes],
        *,
        ops: list[dict] | None = None,
        preset: str | None = None,
        export_format: str = "png",
    ) -> dict:
        """Apply the same pipeline to several images (batch / sync settings)."""
        return self._studio.batch_edit_images(
            images, ops=ops, preset=preset, export_format=export_format
        )

    # --- non-destructive edit sessions (undo / redo / history) ---------------

    def begin_image_session(self, data: bytes) -> dict:
        """Start a non-destructive edit session around an image."""
        return self._studio.begin_image_session(data)

    def edit_image_session(
        self, session_id: str, ops: list[dict], *, export_format: str = "png"
    ) -> dict:
        """Apply a step to a session and record it in the undo stack."""
        return self._studio.edit_image_session(
            session_id, ops, export_format=export_format
        )

    def undo_image_session(
        self, session_id: str, *, export_format: str = "png"
    ) -> dict:
        """Undo the last edit step."""
        return self._studio.undo_image_session(session_id, export_format=export_format)

    def redo_image_session(
        self, session_id: str, *, export_format: str = "png"
    ) -> dict:
        """Redo the last undone edit step."""
        return self._studio.redo_image_session(session_id, export_format=export_format)

    def image_session_state(self, session_id: str) -> dict:
        """Current state of a session (version, undo/redo availability)."""
        return self._studio.image_session_state(session_id)

    # --- video & audio effects + accessibility -------------------------------

    def video_effect_catalog(self) -> dict:
        """Every video frame effect with a plain-language description."""
        from .. import video_effects

        return video_effects.effect_catalog()

    def apply_video_effect(
        self,
        data: bytes,
        name: str,
        params: dict | None = None,
        *,
        export_format: str = "png",
    ) -> dict:
        """Apply a frame effect to an image (or a video frame) and persist it."""
        import numpy as np
        from PIL import Image as PILImage

        from .. import image_engine, video_effects

        img = image_engine.load_image(data)
        frame = np.asarray(img.convert("RGB"))
        result = video_effects.apply_frame_effect(frame, name, params)
        out = PILImage.fromarray(result, mode="RGB")
        blob = image_engine.export_bytes(out, export_format)
        return self._studio.edit_image_bytes(blob, ops=[], export_format=export_format)

    def audio_effect_catalog(self) -> dict:
        """Every audio effect with a plain-language description."""
        from .. import audio_effects

        return audio_effects.audio_effect_catalog()

    def apply_audio_effect(
        self,
        data: bytes,
        name: str,
        params: dict | None = None,
        *,
        export_format: str = "mp3",
    ) -> dict:
        """Apply a DSP effect to audio bytes and persist the result."""
        from .. import audio_effects, voice_engine

        samples, sr = voice_engine.decode_to_pcm(data)
        processed = audio_effects.apply_audio_effect(samples, sr, name, params)
        blob = voice_engine.encode_pcm(processed, sr, export_format)
        return self._studio.persist_audio_bytes(blob, export_format)

    def video_operation_catalog(self) -> dict:
        """Every video/audio operation grouped by category, with descriptions."""
        from .. import video_assist

        return video_assist.catalog()

    def describe_video_operation(self, name: str) -> dict:
        """Explain one video/audio operation in plain language."""
        from .. import video_assist

        return video_assist.describe_operation(name)

    def describe_video_timeline(self, project_id: str) -> dict:
        """Summarise a project's timeline in natural language."""
        from .. import video_assist

        project = self.get_project(project_id)
        if project.video_project is None:
            raise StateConflictError("No video project yet.")
        return video_assist.describe_timeline(project.video_project)

    def suggest_video_edits(self, project_id: str) -> dict:
        """Turn the timeline report into concrete edit suggestions."""
        from .. import video_assist

        project = self.get_project(project_id)
        if project.video_project is None:
            raise StateConflictError("No video project yet.")
        return video_assist.suggest_edits(project.video_project)

    def image_presets(self) -> list[str]:
        """Named one-click photo looks."""
        return sorted(IMAGE_PRESETS)

    def voice_presets(self) -> list[str]:
        """Named Audition-style voice chains."""
        return list(VOICE_PRESETS_DOC)

    def process_voice_audio(
        self,
        data: bytes,
        *,
        params: dict | None = None,
        preset: str | None = None,
        export_format: str = "mp3",
    ) -> dict:
        """Enhance raw voice audio through the Audition-style chain."""
        return self._studio.process_voice_bytes(
            data, params=params, preset=preset, export_format=export_format
        )

    def duck_music_under_voice(
        self, voice: bytes, music: bytes, duck_db: float = -12.0
    ) -> dict:
        """Mix a music bed that automatically ducks under the voice."""
        return self._studio.duck_music_bytes(voice, music, duck_db=duck_db)

    def edited_asset_path(self, name: str) -> Path:
        """Absolute path of a persisted edited asset (image or audio)."""
        try:
            return self._studio.asset_path(name)
        except FileNotFoundError as exc:
            raise NotFoundError(str(exc)) from exc

    def render_video(
        self, project_id: str, export_format: str = "webm", audio_ref: str | None = None
    ) -> Project:
        if export_format not in {"webm", "mp4"}:
            raise ValueError("export_format must be webm or mp4.")
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
                raise StateConflictError(
                    "Project changed during rendering; export discarded."
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
