"""Video timeline NLE: scenes, retime, markers, report and render plan."""

from __future__ import annotations

from collections.abc import Callable

from .. import smart, timeline
from ..models import (
    Keyframe,
    Project,
    ProjectStatus,
    RenderPlan,
    TimelineReport,
    VideoProject,
    VideoScene,
    utcnow,
)
from .context import ServiceContext
from .errors import (
    NotFoundError,
    StateConflictError,
)


class TimelineMixin(ServiceContext):
    """Video timeline NLE: scenes, retime, markers, report and render plan."""

    def build_video_project(self, project_id: str) -> Project:
        """(Re)build the editable video project from the current script.

        Scene ids survive the rebuild (see ``_rebuild_video_project``), so a
        client that holds one can keep editing after rebuilding.
        """
        project = self.get_project(project_id).model_copy(deep=True)
        video_project = self._rebuild_video_project(project)
        self._store_video_project(project, video_project)
        self._attach_source_footage(project)
        return self._store.save(project)

    def update_video_project(self, project_id: str, edit: VideoProject) -> Project:
        """Persist the user's edits, repairing the document on the way in.

        Every save is normalized, so a partially-built or hostile client can
        never persist a broken timeline.
        """
        project = self.get_project(project_id).model_copy(deep=True)
        self._assert_video_editable(project)
        self._store_video_project(project, edit)
        return self._store.save(project)

    # --- Timeline engine ------------------------------------------------------

    def _assert_video_editable(self, project: Project) -> None:
        # A published cut stays editable: re-cutting and re-publishing is a
        # normal workflow, unlike rewriting an approved script.
        if project.status not in (
            ProjectStatus.GENERATING,
            ProjectStatus.VIDEO_REVIEW,
            ProjectStatus.VIDEO_APPROVED,
            ProjectStatus.PUBLISHED,
        ):
            msg = f"Cannot edit the video while status is '{project.status.value}'."
            raise StateConflictError(msg)

    def _editable_video_project(self, project: Project) -> VideoProject:
        """Return the project's timeline, or explain why it cannot be edited."""
        if project.video_project is None:
            raise StateConflictError("No video project yet.")
        self._assert_video_editable(project)
        return project.video_project

    def _store_video_project(
        self, project: Project, video_project: VideoProject
    ) -> None:
        """Normalize, bump the revision, and attach a timeline to a project.

        The revision counter is server-owned: a client cannot jump it by
        sending its own value, so it stays a reliable "someone else moved the
        timeline" signal for concurrent editors and external agents.
        """
        video_project = video_project.model_copy(deep=True)
        timeline.normalize(video_project)
        previous = project.video_project
        base = previous.revision if previous is not None else 1
        video_project.revision = max(1, base) + 1
        video_project.updated_at = utcnow()
        project.video_project = video_project

    def _apply_timeline_edit(
        self, project_id: str, edit: Callable[[VideoProject], object]
    ) -> Project:
        """Run one timeline operation against the stored project."""
        project = self.get_project(project_id).model_copy(deep=True)
        video_project = self._editable_video_project(project).model_copy(deep=True)
        try:
            edit(video_project)
        except KeyError as exc:
            raise NotFoundError(str(exc)) from exc
        except (ValueError, TypeError) as exc:
            raise StateConflictError(str(exc)) from exc
        self._store_video_project(project, video_project)
        return self._store.save(project)

    def split_video_scene(
        self, project_id: str, scene_id: str, at: float = 0.5
    ) -> Project:
        """Split a scene in two at a fraction of its runtime."""
        return self._apply_timeline_edit(
            project_id, lambda video: timeline.split_scene(video, scene_id, at)
        )

    def merge_video_scene(self, project_id: str, scene_id: str) -> Project:
        """Merge a scene into the following one."""
        return self._apply_timeline_edit(
            project_id, lambda video: timeline.merge_scene(video, scene_id)
        )

    def duplicate_video_scene(self, project_id: str, scene_id: str) -> Project:
        """Insert a copy of a scene directly after it."""
        return self._apply_timeline_edit(
            project_id, lambda video: timeline.duplicate_scene(video, scene_id)
        )

    def delete_video_scene(self, project_id: str, scene_id: str) -> Project:
        """Remove a scene (never the last one)."""
        return self._apply_timeline_edit(
            project_id, lambda video: timeline.delete_scene(video, scene_id)
        )

    def move_video_scene(
        self, project_id: str, scene_id: str, to_index: int
    ) -> Project:
        """Reorder a scene on the timeline."""
        return self._apply_timeline_edit(
            project_id, lambda video: timeline.move_scene(video, scene_id, to_index)
        )

    def bulk_update_video_scenes(
        self, project_id: str, scene_ids: list[str], patch: dict
    ) -> Project:
        """Apply one look to many scenes at once."""
        return self._apply_timeline_edit(
            project_id,
            lambda video: timeline.bulk_update(video, scene_ids, patch),
        )

    def set_scene_speed(self, project_id: str, scene_id: str, speed: float) -> Project:
        """Retime one scene (0.5x .. 2x), like an NLE's speed dialog."""
        return self._apply_timeline_edit(
            project_id, lambda video: timeline.set_speed(video, scene_id, speed)
        )

    def reverse_scene(
        self, project_id: str, scene_id: str, reverse: bool = True
    ) -> Project:
        """Play a scene's source backwards."""
        return self._apply_timeline_edit(
            project_id, lambda video: timeline.reverse_scene(video, scene_id, reverse)
        )

    def trim_scene(
        self,
        project_id: str,
        scene_id: str,
        trim_start: float | None,
        trim_end: float | None,
    ) -> Project:
        """Set a scene's source in/out handles."""
        return self._apply_timeline_edit(
            project_id,
            lambda video: timeline.trim_scene(video, scene_id, trim_start, trim_end),
        )

    def set_scene_audio(
        self,
        project_id: str,
        scene_id: str,
        volume: float | None,
        fade_in: float | None,
        fade_out: float | None,
    ) -> Project:
        """Adjust a scene's gain and audio fades."""
        return self._apply_timeline_edit(
            project_id,
            lambda video: timeline.set_audio(
                video, scene_id, volume, fade_in, fade_out
            ),
        )

    def copy_scene(self, project_id: str, scene_id: str) -> dict:
        """Copy a scene to a JSON clipboard the client can paste later."""
        project = self.get_project(project_id)
        video_project = self._editable_video_project(project).model_copy(deep=True)
        try:
            clip = timeline.copy_scene(video_project, scene_id)
        except KeyError as exc:
            raise NotFoundError(str(exc)) from exc
        return clip.model_dump(mode="json")

    def paste_scene(
        self, project_id: str, clip: dict, after_scene_id: str | None
    ) -> Project:
        """Paste a scene previously returned by copy_scene."""
        scene = VideoScene.model_validate(clip)
        return self._apply_timeline_edit(
            project_id,
            lambda video: timeline.paste_scene(video, scene, after_scene_id),
        )

    def normalize_video_project(self, project_id: str) -> Project:
        """Repair the timeline and record it as a new revision."""
        return self._apply_timeline_edit(project_id, lambda video: None)

    def add_timeline_marker(
        self, project_id: str, time_seconds: float, label: str, color: str
    ) -> Project:
        """Add a labelled marker to the timeline."""
        return self._apply_timeline_edit(
            project_id,
            lambda video: timeline.add_marker(video, time_seconds, label, color),
        )

    def set_scene_keyframes(
        self, project_id: str, scene_id: str, keyframes: list[dict]
    ) -> Project:
        """Replace a scene's motion keyframe track from raw dicts."""
        frames = [Keyframe.model_validate(frame) for frame in keyframes]
        return self._apply_timeline_edit(
            project_id,
            lambda video: timeline.set_keyframes(video, scene_id, frames),
        )

    def remove_timeline_marker(self, project_id: str, marker_id: str) -> Project:
        """Remove a marker by id."""
        return self._apply_timeline_edit(
            project_id, lambda video: timeline.remove_marker(video, marker_id)
        )

    def timeline_report(self, project_id: str) -> TimelineReport:
        """Measure and validate the timeline."""
        project = self.get_project(project_id)
        if project.video_project is None:
            raise StateConflictError("No video project yet.")
        return timeline.report(
            project.video_project, target_seconds=project.duration_target_seconds
        )

    def render_plan(self, project_id: str) -> RenderPlan:
        """Compile the timeline into an absolute render plan."""
        project = self.get_project(project_id)
        if project.video_project is None:
            raise StateConflictError("No video project yet.")
        narration_urls = {
            track.scene_id: track.audio_url
            for track in (project.voiceover.tracks if project.voiceover else [])
        }
        return timeline.compile_render_plan(
            project.video_project.model_copy(deep=True),
            project_id=project.id,
            narration_urls=narration_urls,
        )

    def apply_ai_assist(
        self, project_id: str, *, fit: bool, beat: bool, bpm: int
    ) -> Project:
        """Run the AI auto-edit pipeline over the video project."""
        return self._apply_timeline_edit(
            project_id,
            lambda video: smart.apply_ai_assist(video, fit=fit, beat=beat, bpm=bpm),
        )

    def ai_suggest_scene(self, project_id: str, scene_id: str) -> dict[str, str]:
        """Ask the AI for filter/effect/grade/transition suggestions on a scene."""
        project = self.get_project(project_id)
        if project.video_project is None:
            raise StateConflictError("No video project yet.")
        scene = next(
            (s for s in project.video_project.scenes if s.id == scene_id), None
        )
        if scene is None:
            raise NotFoundError(f"No scene '{scene_id}' in the video project.")
        return smart.suggest_all(scene)

    def polish_scene_text(self, project_id: str, scene_id: str) -> Project:
        """AI-polish a single scene's text."""

        def polish(video: VideoProject) -> None:
            scene = next((s for s in video.scenes if s.id == scene_id), None)
            if scene is None:
                raise NotFoundError(f"No scene '{scene_id}' in the video project.")
            scene.text = smart.polish_text(scene.text)

        return self._apply_timeline_edit(project_id, polish)
