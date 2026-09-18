"""Node/edge workflow authoring, validation and background runs."""

from __future__ import annotations

import threading
import uuid

from .. import workflow
from ..models import (
    Project,
    Workflow,
    WorkflowChecklist,
    WorkflowRun,
    WorkflowRunRequest,
    WorkflowRunStatus,
    WorkflowSave,
    utcnow,
)
from ..workflow import WorkflowChecklistError
from .agents import AgentsMixin
from .errors import (
    NotFoundError,
)
from .growth import GrowthMixin
from .projects import ProjectsMixin
from .voice import VoiceMixin

#: The run registry keeps a bounded window of history; it is a monitoring
#: aid, not an archive, so the oldest records are evicted past this cap.
_MAX_WORKFLOW_RUNS = 500


class WorkflowMixin(AgentsMixin, ProjectsMixin, GrowthMixin, VoiceMixin):
    """Node/edge workflow authoring, validation and background runs."""

    # --- Drag-and-drop production flows ---------------------------------------

    def project_workflow(self, project_id: str) -> Workflow:
        """The project's flow, or a fresh copy of the default one."""
        return workflow.project_flow(self.get_project(project_id))

    def workflow_checklist(self, project_id: str) -> WorkflowChecklist:
        """Pre-save checklist for the stored flow (or the default one)."""
        return workflow.checklist(self.project_workflow(project_id))

    def block_catalog(self) -> list[dict]:
        """The palette of blocks the flow canvas can offer."""
        return workflow.describe_blocks()

    def validate_workflow(
        self, project_id: str, data: WorkflowSave
    ) -> WorkflowChecklist:
        """Check a candidate flow without saving it.

        The canvas asks this on every edit, so the checklist describes what the
        operator is actually looking at rather than the last saved version.
        """
        self.get_project(project_id)
        flow = workflow.normalize_workflow(data.workflow.model_copy(deep=True))
        return workflow.checklist(flow)

    def save_workflow(self, project_id: str, data: WorkflowSave) -> Project:
        """Save a flow as a new version.

        Mirrors an automation builder: an unfinished flow cannot be saved
        unless the operator explicitly forces it.
        """
        project = self.get_project(project_id)
        flow = workflow.normalize_workflow(data.workflow.model_copy(deep=True))
        result = workflow.checklist(flow)
        if not result.ready and not data.force:
            raise WorkflowChecklistError(result)
        previous = project.workflow.version if project.workflow else 0
        flow.version = previous + 1
        flow.updated_at = utcnow()
        project.workflow = flow
        return self._store.save(project)

    def synthesize_voiceover(self, project_id: str) -> Project:
        """Synthesize narration synchronously, for flow blocks.

        Applies the same guards as the API entry point, so narration cannot
        run behind a disabled engine just because an operator wired it into a
        flow.
        """
        project = self._assert_tts_available(project_id)
        self._synthesize_voiceover(project_id)
        return self.get_project(project.id)

    def run_workflow(self, project_id: str, data: WorkflowRunRequest) -> WorkflowRun:
        """Run the stored flow against the project, synchronously."""
        project = self.get_project(project_id)
        runner = workflow.WorkflowRunner(self)
        run = runner.run(
            project_id,
            workflow=workflow.project_flow(project),
            inputs=dict(data.inputs),
        )
        self._remember_run(run)
        return run

    def start_workflow(self, project_id: str, data: WorkflowRunRequest) -> WorkflowRun:
        """Start a flow run in the background and return the pending record."""
        self.get_project(project_id)
        run = WorkflowRun(
            id=uuid.uuid4().hex[:12],
            project_id=project_id,
            inputs=dict(data.inputs),
        )
        self._remember_run(run)
        self._register_worker(
            threading.Thread(
                target=self._run_workflow_thread,
                args=(project_id, run.id, dict(data.inputs)),
                name=f"workflow-{run.id}",
                daemon=True,
            )
        )
        return run

    def _run_workflow_thread(self, project_id: str, run_id: str, inputs: dict) -> None:
        """Run a flow in the background, publishing progress block by block."""

        def publish(run: WorkflowRun) -> None:
            self._remember_run(run.model_copy(deep=True))

        try:
            project = self.get_project(project_id)
            runner = workflow.WorkflowRunner(self)
            finished = runner.run(
                project_id,
                workflow=workflow.project_flow(project),
                inputs=inputs,
                on_progress=publish,
                run_id=run_id,
            )
        except Exception as exc:
            finished = WorkflowRun(
                id=run_id,
                project_id=project_id,
                inputs=inputs,
                status=WorkflowRunStatus.FAILED,
                message=str(exc),
                finished_at=utcnow(),
            )
        publish(finished)

    def _remember_run(self, run: WorkflowRun) -> None:
        """Store a run record, evicting the oldest ones past the cap."""
        with self._workflow_lock:
            self._workflow_runs[run.id] = run
            excess = len(self._workflow_runs) - _MAX_WORKFLOW_RUNS
            if excess > 0:
                oldest = sorted(
                    self._workflow_runs.values(), key=lambda item: item.started_at
                )[:excess]
                for item in oldest:
                    self._workflow_runs.pop(item.id, None)

    def workflow_runs(self, project_id: str, limit: int = 20) -> list[WorkflowRun]:
        """Recent runs for a project, newest first."""
        with self._workflow_lock:
            runs = [
                run
                for run in self._workflow_runs.values()
                if run.project_id == project_id
            ]
        runs.sort(key=lambda run: run.started_at, reverse=True)
        return runs[:limit]

    def workflow_run(self, run_id: str) -> WorkflowRun:
        """One run record, for the monitoring panel."""
        with self._workflow_lock:
            run = self._workflow_runs.get(run_id)
        if run is None:
            raise NotFoundError(f"No workflow run '{run_id}'.")
        return run
