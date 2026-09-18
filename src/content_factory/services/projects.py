"""Project lifecycle: creation, script edits, approvals and publishing."""

from __future__ import annotations

from pathlib import Path

from ..models import (
    ApprovalCreate,
    ApprovalRecord,
    ApprovalStage,
    ApprovalVerdict,
    Project,
    ProjectCreate,
    ProjectStatus,
    PublishCreate,
    ScriptUpdate,
    VideoAsset,
    utcnow,
)
from .context import ServiceContext
from .errors import (
    RightsNotConfirmedError,
    StateConflictError,
)


class ProjectsMixin(ServiceContext):
    """Project lifecycle: creation, script edits, approvals and publishing."""

    def create_project(self, data: ProjectCreate) -> Project:
        return self._store.create(data)

    def list_projects(self) -> list[Project]:
        return self._store.list()

    def update_script(self, project_id: str, data: ScriptUpdate) -> Project:
        """Save a script (human-written or edited) and optional rights flag."""
        project = self.get_project(project_id)
        if project.status not in (ProjectStatus.DRAFT, ProjectStatus.SCRIPT_REVIEW):
            raise StateConflictError(
                f"Cannot edit the script while status is '{project.status.value}'."
            )
        project.script = data.script
        project.source_rights_confirmed = data.source_rights_confirmed
        if project.status == ProjectStatus.DRAFT:
            self._transition(project, ProjectStatus.SCRIPT_REVIEW)
        self._refresh_analysis(project)
        return self._store.save(project)

    def approve(self, project_id: str, data: ApprovalCreate) -> Project:
        """Record a human review decision on a project gate."""
        project = self.get_project(project_id)
        if data.stage == ApprovalStage.SCRIPT:
            self._approve_script(project, data)
        elif data.stage == ApprovalStage.VIDEO:
            self._approve_video(project, data)
        else:
            raise StateConflictError(f"Unknown approval stage '{data.stage}'.")
        project.approvals.append(
            ApprovalRecord(stage=data.stage, verdict=data.verdict, comment=data.comment)
        )
        return self._store.save(project)

    def _approve_script(self, project: Project, data: ApprovalCreate) -> None:
        if project.status != ProjectStatus.SCRIPT_REVIEW:
            msg = f"Cannot review script while status is '{project.status.value}'."
            raise StateConflictError(msg)
        if (
            data.verdict == ApprovalVerdict.APPROVED
            and not project.source_rights_confirmed
        ):
            raise RightsNotConfirmedError(
                "source_rights_confirmed must be true before approving the script."
            )
        if data.verdict == ApprovalVerdict.APPROVED:
            self._transition(project, ProjectStatus.SCRIPT_APPROVED)

    def _approve_video(self, project: Project, data: ApprovalCreate) -> None:
        if project.status != ProjectStatus.VIDEO_REVIEW:
            msg = f"Cannot review video while status is '{project.status.value}'."
            raise StateConflictError(msg)
        if data.verdict == ApprovalVerdict.APPROVED:
            self._transition(project, ProjectStatus.VIDEO_APPROVED)

    def start_generation(self, project_id: str) -> Project:
        """Start (or restart) video production and kick off the worker."""
        project = self.get_project(project_id)
        if project.status not in (
            ProjectStatus.SCRIPT_APPROVED,
            ProjectStatus.FAILED,
            ProjectStatus.VIDEO_REVIEW,
        ):
            msg = f"Cannot start generation while status is '{project.status.value}'."
            raise StateConflictError(msg)
        self._transition(project, ProjectStatus.GENERATING)
        project.progress = 0
        project.video = None
        project.error = None
        self._store.save(project)
        self._spawn_worker(project_id)
        return project

    def produce_video(self, project_id: str) -> Project:
        """Produce the video synchronously, for flow blocks.

        The deterministic counterpart of the background worker: a
        script-approved project moves straight into review with a fresh
        editable timeline, so a flow run has no thread to race against.
        A project that already has a timeline is left alone.
        """
        project = self.get_project(project_id)
        if project.status == ProjectStatus.GENERATING:
            return self.complete_generation(project_id)
        if project.status not in (ProjectStatus.SCRIPT_APPROVED, ProjectStatus.FAILED):
            if project.video_project is not None:
                return project
            msg = f"Cannot produce the video while status is '{project.status.value}'."
            raise StateConflictError(msg)
        self._transition(project, ProjectStatus.GENERATING)
        project.progress = 100
        project.error = None
        self._store.save(project)
        return self.complete_generation(project_id)

    def upload_video(self, project_id: str, filename: str, content: bytes) -> Project:
        """Store an exported video and attach it to the project."""
        project = self.get_project(project_id)
        if project.status not in (
            ProjectStatus.GENERATING,
            ProjectStatus.VIDEO_REVIEW,
            ProjectStatus.VIDEO_APPROVED,
        ):
            msg = f"Cannot upload a video while status is '{project.status.value}'."
            raise StateConflictError(msg)
        videos_dir = Path(self._settings.library_dir) / "videos"
        videos_dir.mkdir(parents=True, exist_ok=True)
        dest = videos_dir / f"{project.id}.webm"
        dest.write_bytes(content)
        duration = 0
        if project.video_project is not None:
            duration = int(
                sum(scene.duration_seconds for scene in project.video_project.scenes)
            )
        project.video = VideoAsset(
            asset_url=f"/projects/{project.id}/video",
            thumbnail_url=f"/projects/{project.id}/thumbnail",
            duration_seconds=duration or project.duration_target_seconds,
            format="webm",
            size_bytes=len(content),
        )
        if project.status == ProjectStatus.GENERATING:
            self._transition(project, ProjectStatus.VIDEO_REVIEW)
        return self._store.save(project)

    def publish(self, project_id: str, data: PublishCreate) -> Project:
        """Publish an approved video to the requested platforms."""
        project = self.get_project(project_id)
        self._transition(project, ProjectStatus.PUBLISHED)
        project.platforms = list(data.platforms)
        project.published_at = utcnow()
        return self._store.save(project)

    def video_path(self, project_id: str) -> Path | None:
        """Absolute path of the exported video file, if it exists."""
        project = self.get_project(project_id)
        export_format = project.video.format if project.video else "webm"
        if export_format not in {"webm", "mp4"}:
            return None
        candidate = (
            Path(self._settings.library_dir)
            / "videos"
            / f"{project.id}.{export_format}"
        )
        return candidate if candidate.is_file() else None
