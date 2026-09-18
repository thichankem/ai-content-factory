"""Drag-and-drop production flows: validate, order, and execute blocks.

A :class:`~content_factory.models.Workflow` is a small node graph: blocks
(:class:`WorkflowNode`) connected by links (:class:`WorkflowEdge`). Running a
flow executes its blocks in dependency order, feeding each block the outputs of
its predecessors, and records everything an operator needs to debug it.

Three jobs:

* :func:`checklist` — the pre-save gate. It reports unfinished blocks (blank
  labels, missing parameters, blocks with no incoming link, unreachable
  branches, cycles) exactly like an automation builder's checklist, and
  resolves the execution order.
* :func:`topological_order` — dependency order with deterministic tie-breaking,
  so a run is reproducible.
* :class:`WorkflowRunner` — executes the blocks against a live project by
  calling the same service methods the REST API uses. Nothing here re-implements
  a pipeline step.

The human review gates are honoured, not bypassed: a ``gate`` block checks the
approval state and, when it is missing, the run stops as ``blocked`` instead of
pushing the project forward behind the operator's back.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from typing import Any, Protocol

from .models import (
    ApprovalStage,
    ExternalAssetRecord,
    ExternalImportRequest,
    IssueSeverity,
    Project,
    ProjectStatus,
    PublishCreate,
    RenderPlan,
    ScriptAnalysis,
    ScriptAnalyzeRequest,
    TimelineReport,
    Workflow,
    WorkflowCheckIssue,
    WorkflowChecklist,
    WorkflowEdge,
    WorkflowNode,
    WorkflowNodeType,
    WorkflowRun,
    WorkflowRunStatus,
    WorkflowStepResult,
    WorkflowStepStatus,
    utcnow,
)


class WorkflowService(Protocol):
    """The slice of the service layer a flow run actually needs.

    Declaring it here inverts the dependency: the flow engine no longer knows
    about the concrete service class, only about the operations it invokes,
    which keeps the two modules free to evolve independently.
    """

    def get_project(self, project_id: str) -> Project: ...

    async def research(self, project_id: str, include_web: bool = True) -> Project: ...

    async def generate_script(self, project_id: str) -> Project: ...

    def analyze_project_script(
        self, project_id: str, request: ScriptAnalyzeRequest
    ) -> ScriptAnalysis: ...

    def produce_video(self, project_id: str) -> Project: ...

    def synthesize_voiceover(self, project_id: str) -> Project: ...

    def apply_ai_assist(
        self, project_id: str, *, fit: bool, beat: bool, bpm: int
    ) -> Project: ...

    def timeline_report(self, project_id: str) -> TimelineReport: ...

    def render_plan(self, project_id: str) -> RenderPlan: ...

    def publish(self, project_id: str, data: PublishCreate) -> Project: ...

    def batch_import_external_assets(
        self, project_id: str, requests: list[ExternalImportRequest]
    ) -> list[ExternalAssetRecord]: ...


def _run_sync(coro: Any) -> Any:
    """Run an async coroutine synchronously.

    Handles both active and non-active event loops safely.
    """
    import asyncio
    import concurrent.futures

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    return asyncio.run(coro)


#: Human-readable name for each block type.
NODE_LABELS: dict[WorkflowNodeType, str] = {
    WorkflowNodeType.RESEARCH: "Research sources",
    WorkflowNodeType.SCRIPT: "Draft script",
    WorkflowNodeType.LINT: "Lint script",
    WorkflowNodeType.GATE: "Human gate",
    WorkflowNodeType.VOICEOVER: "Narrate scenes",
    WorkflowNodeType.SCENES: "Produce video",
    WorkflowNodeType.AI_ASSIST: "AI auto-edit",
    WorkflowNodeType.TIMELINE_CHECK: "Validate cut",
    WorkflowNodeType.RENDER_PLAN: "Compile render plan",
    WorkflowNodeType.PUBLISH: "Publish",
    WorkflowNodeType.INGEST_EXTERNAL: "Ingest external media",
}

#: One-line description shown in the palette and the inspector.
NODE_DESCRIPTIONS: dict[WorkflowNodeType, str] = {
    WorkflowNodeType.RESEARCH: "Gather reference sources and key facts for the topic.",
    WorkflowNodeType.SCRIPT: "Draft an original script via the provider chain.",
    WorkflowNodeType.LINT: "Score the script: style, timing, and copy-risk findings.",
    WorkflowNodeType.GATE: "A mandatory human review. Blocks the run until it passes.",
    WorkflowNodeType.VOICEOVER: "Synthesize narration and re-sync scene timing.",
    WorkflowNodeType.SCENES: "Build the editable timeline and enter review.",
    WorkflowNodeType.AI_ASSIST: "Auto-fit durations, beat-sync, and pick a look.",
    WorkflowNodeType.TIMELINE_CHECK: "Validate the cut: contrast, overflow, pacing.",
    WorkflowNodeType.RENDER_PLAN: "Compile the timeline into render instructions.",
    WorkflowNodeType.PUBLISH: "Send the approved video to the configured platforms.",
    WorkflowNodeType.INGEST_EXTERNAL: (
        "Import external AI footage (Kling/Veo), images (Midjourney), or audio."
    ),
}

#: Node types whose parameters must be filled in before saving.
REQUIRED_PARAMS: dict[WorkflowNodeType, tuple[str, ...]] = {
    WorkflowNodeType.GATE: ("stage",),
    WorkflowNodeType.PUBLISH: ("platforms",),
}

_VALID_GATES = {stage.value for stage in ApprovalStage}

#: Statuses in which a timeline already exists and must not be rebuilt.
_PRODUCED_STATUSES = frozenset(
    {
        ProjectStatus.GENERATING,
        ProjectStatus.VIDEO_REVIEW,
        ProjectStatus.VIDEO_APPROVED,
        ProjectStatus.PUBLISHED,
    }
)


def default_workflow() -> Workflow:
    """The stock flow: research, script, lint, script gate, then production.

    Laid out left to right on the canvas so a new project opens with a usable
    flow the operator can rearrange by dragging.
    """
    layout: list[tuple[WorkflowNodeType, dict[str, Any], float]] = [
        (WorkflowNodeType.RESEARCH, {"include_web": True}, 0),
        (WorkflowNodeType.SCRIPT, {}, 1),
        (WorkflowNodeType.LINT, {}, 2),
        (WorkflowNodeType.GATE, {"stage": ApprovalStage.SCRIPT.value}, 3),
        (WorkflowNodeType.SCENES, {}, 4),
        (WorkflowNodeType.VOICEOVER, {}, 5),
        (WorkflowNodeType.AI_ASSIST, {"fit": True, "beat": True, "bpm": 120}, 6),
        (WorkflowNodeType.TIMELINE_CHECK, {}, 7),
        (WorkflowNodeType.RENDER_PLAN, {}, 8),
    ]
    nodes: list[WorkflowNode] = []
    edges: list[WorkflowEdge] = []
    for index, (node_type, params, column) in enumerate(layout):
        nodes.append(
            WorkflowNode(
                id=f"n{index + 1}",
                type=node_type,
                label=NODE_LABELS[node_type],
                x=40.0 + column * 210.0,
                y=180.0,
                params=params,
            )
        )
        if index:
            edges.append(
                WorkflowEdge(
                    id=f"e{index}",
                    source=nodes[index - 1].id,
                    target=nodes[index].id,
                )
            )
    return Workflow(nodes=nodes, edges=edges, version=1)


def node_label(node: WorkflowNode) -> str:
    """Display label for a block, falling back to its type name."""
    return (node.label or "").strip() or NODE_LABELS.get(node.type, str(node.type))


def normalize_workflow(workflow: Workflow) -> Workflow:
    """Repair a flow in place: unique ids, valid links, no self-loops.

    Idempotent, like the timeline normalizer. Links pointing at missing blocks
    are dropped rather than rejected, so deleting a block in the UI can never
    leave a corrupt graph behind.
    """
    seen: set[str] = set()
    for node in workflow.nodes:
        candidate = (node.id or "").strip()
        if not candidate or candidate in seen:
            candidate = uuid.uuid4().hex[:8]
            while candidate in seen:
                candidate = uuid.uuid4().hex[:8]
        node.id = candidate
        seen.add(candidate)
        node.label = (node.label or "").strip()[:120]
        node.x = float(node.x or 0.0)
        node.y = float(node.y or 0.0)

    known = {node.id for node in workflow.nodes}
    kept: list[WorkflowEdge] = []
    source_groups: dict[str, set[str]] = {}
    for edge in workflow.edges:
        if edge.source not in known or edge.target not in known:
            continue
        if edge.source == edge.target:
            continue
        if edge.target in source_groups.setdefault(edge.source, set()):
            continue
        source_groups[edge.source].add(edge.target)
        edge.id = (edge.id or "").strip() or uuid.uuid4().hex[:8]
        kept.append(edge)
    workflow.edges = kept
    workflow.version = max(1, int(workflow.version or 1))
    return workflow


def incoming(workflow: Workflow, node_id: str) -> list[WorkflowEdge]:
    return [edge for edge in workflow.edges if edge.target == node_id]


def outgoing(workflow: Workflow, node_id: str) -> list[WorkflowEdge]:
    return [edge for edge in workflow.edges if edge.source == node_id]


def topological_order(workflow: Workflow) -> tuple[list[str], list[str]]:
    """Return ``(order, blocked_node_ids)``.

    Order is deterministic: ready nodes are taken in canvas reading order (top
    to bottom, then left to right), so the same flow always runs the same way.
    Nodes left over because they sit in a cycle are returned as blocked.
    """
    position = {node.id: index for index, node in enumerate(workflow.nodes)}
    remaining = {node.id for node in workflow.nodes}
    dependencies = {
        node.id: {edge.source for edge in incoming(workflow, node.id)}
        for node in workflow.nodes
    }
    order: list[str] = []
    while remaining:
        ready = [
            node_id for node_id in remaining if not (dependencies[node_id] & remaining)
        ]
        if not ready:
            break
        ready.sort(key=lambda node_id: position[node_id])
        for node_id in ready:
            order.append(node_id)
            remaining.discard(node_id)
    return order, sorted(remaining, key=lambda node_id: position[node_id])


def checklist(workflow: Workflow) -> WorkflowChecklist:
    """Pre-save validation: unfinished blocks, bad wiring, cycles."""
    issues: list[WorkflowCheckIssue] = []
    nodes = workflow.nodes
    ids = [node.id for node in nodes]

    if not nodes:
        issues.append(
            WorkflowCheckIssue(
                code="empty_flow",
                severity=IssueSeverity.ERROR,
                message="The flow has no blocks.",
                hint="Drag a block from the palette onto the canvas.",
            )
        )
        return WorkflowChecklist(issues=issues, ready=False)

    if len(ids) != len(set(ids)):
        issues.append(
            WorkflowCheckIssue(
                code="duplicate_block_id",
                severity=IssueSeverity.ERROR,
                message="Two blocks share the same id.",
                hint="Save the flow to repair ids automatically.",
            )
        )

    known = set(ids)
    for edge in workflow.edges:
        if edge.source not in known or edge.target not in known:
            issues.append(
                WorkflowCheckIssue(
                    code="dangling_link",
                    severity=IssueSeverity.ERROR,
                    message="A link points at a block that no longer exists.",
                    hint="Save the flow to drop the orphaned link.",
                )
            )
            break

    order, cyclic = topological_order(workflow)
    entry_id = order[0] if order else None

    for node in nodes:
        label = node_label(node)
        if not (node.label or "").strip():
            issues.append(
                WorkflowCheckIssue(
                    code="unnamed_block",
                    severity=IssueSeverity.WARNING,
                    message=f"A {node.type.value} block has no name.",
                    hint="Give it a name in the inspector so the flow reads clearly.",
                    node_id=node.id,
                )
            )
        for key in REQUIRED_PARAMS.get(node.type, ()):
            value = node.params.get(key)
            if value in (None, "", [], {}):
                issues.append(
                    WorkflowCheckIssue(
                        code="missing_param",
                        severity=IssueSeverity.ERROR,
                        message=f"'{label}' is missing the '{key}' setting.",
                        hint="Open the block and complete its settings.",
                        node_id=node.id,
                    )
                )
        if node.type == WorkflowNodeType.GATE:
            stage = str(node.params.get("stage") or "")
            if stage and stage not in _VALID_GATES:
                issues.append(
                    WorkflowCheckIssue(
                        code="invalid_param",
                        severity=IssueSeverity.ERROR,
                        message=f"'{label}' has an unknown gate stage '{stage}'.",
                        hint=f"Use one of: {', '.join(sorted(_VALID_GATES))}.",
                        node_id=node.id,
                    )
                )
        if not incoming(workflow, node.id) and not outgoing(workflow, node.id):
            issues.append(
                WorkflowCheckIssue(
                    code="unconnected_block",
                    severity=IssueSeverity.WARNING,
                    message=f"'{label}' is not connected to anything.",
                    hint="Drag from its + handle into the next block.",
                    node_id=node.id,
                )
            )
        elif not incoming(workflow, node.id) and node.id != entry_id and len(nodes) > 1:
            issues.append(
                WorkflowCheckIssue(
                    code="no_input",
                    severity=IssueSeverity.INFO,
                    message=f"'{label}' has no incoming link; it starts a branch.",
                    hint="That is fine for a second entry point, otherwise link it up.",
                    node_id=node.id,
                )
            )

    if cyclic:
        for node_id in cyclic:
            node = next(item for item in nodes if item.id == node_id)
            issues.append(
                WorkflowCheckIssue(
                    code="cycle",
                    severity=IssueSeverity.ERROR,
                    message=f"'{node_label(node)}' is inside a loop and can never run.",
                    hint="Remove one of the links in the loop.",
                    node_id=node_id,
                )
            )

    gate_stages = [
        str(node.params.get("stage") or "")
        for node in nodes
        if node.type == WorkflowNodeType.GATE
    ]
    if WorkflowNodeType.SCRIPT in {node.type for node in nodes} and (
        ApprovalStage.SCRIPT.value not in gate_stages
    ):
        issues.append(
            WorkflowCheckIssue(
                code="missing_script_gate",
                severity=IssueSeverity.WARNING,
                message="The flow drafts a script but has no script review gate.",
                hint="Add a Human gate set to 'script' so nothing is auto-approved.",
            )
        )

    ready = not any(issue.severity == IssueSeverity.ERROR for issue in issues)
    return WorkflowChecklist(
        issues=issues,
        ready=ready,
        node_count=len(nodes),
        edge_count=len(workflow.edges),
        order=order,
    )


class WorkflowChecklistError(Exception):
    """Raised when a flow fails its pre-save checklist.

    Carries the full checklist so the canvas can highlight every offending
    block at once instead of showing one error per save attempt.
    """

    def __init__(self, result: WorkflowChecklist) -> None:
        errors = [
            issue.message
            for issue in result.issues
            if issue.severity == IssueSeverity.ERROR
        ]
        super().__init__(
            "; ".join(errors) if errors else "The flow is not ready to save."
        )
        self.checklist = result


class WorkflowOrderError(Exception):
    """Raised when a block needs something an earlier block never produced.

    The mirror of :class:`WorkflowBlockedError`: one waits for a human, this
    one means the flow itself is wired in the wrong order.
    """


class WorkflowBlockedError(Exception):
    """Raised when a gate stops the run because a human has not acted yet."""


class WorkflowRunner:
    """Executes a flow against a live project."""

    def __init__(self, service: WorkflowService) -> None:
        self._service = service

    # --- public entry points ---

    def run(
        self,
        project_id: str,
        workflow: Workflow | None = None,
        inputs: dict[str, Any] | None = None,
        on_progress: Callable[[WorkflowRun], None] | None = None,
        run_id: str | None = None,
    ) -> WorkflowRun:
        """Execute the flow and return the full run record.

        ``on_progress`` receives the run after every block, so a monitor can
        watch a long flow fill in block by block instead of waiting for the end.
        ``run_id`` lets the caller name the run up front, which is what makes
        that monitoring possible.
        """
        flow = normalize_workflow(
            workflow.model_copy(deep=True) if workflow else default_workflow()
        )
        run = WorkflowRun(
            id=run_id or uuid.uuid4().hex[:12],
            project_id=project_id,
            inputs=dict(inputs or {}),
            started_at=utcnow(),
        )
        started = time.perf_counter()
        order, cyclic = topological_order(flow)
        by_id = {node.id: node for node in flow.nodes}

        if on_progress:
            on_progress(run)

        for node_id in order:
            node = by_id[node_id]
            run.steps.append(self._step(node, run))
            if on_progress:
                on_progress(run)
            if run.steps[-1].status in (
                WorkflowStepStatus.FAILED,
                WorkflowStepStatus.BLOCKED,
            ):
                run.status = (
                    WorkflowRunStatus.BLOCKED
                    if run.steps[-1].status == WorkflowStepStatus.BLOCKED
                    else WorkflowRunStatus.FAILED
                )
                run.message = run.steps[-1].error
                break

        skipped = list(cyclic)
        for node_id in skipped:
            node = by_id[node_id]
            run.steps.append(
                WorkflowStepResult(
                    node_id=node.id,
                    label=node_label(node),
                    type=node.type,
                    status=WorkflowStepStatus.SKIPPED,
                    error="Blocked by a loop in the flow.",
                )
            )
        if skipped and run.status == WorkflowRunStatus.RUNNING:
            run.status = WorkflowRunStatus.FAILED
            run.message = "The flow contains a loop; some blocks could not run."

        if run.status == WorkflowRunStatus.RUNNING:
            run.status = WorkflowRunStatus.OK
            run.message = f"{len(order)} block(s) executed"
        run.finished_at = utcnow()
        run.duration_ms = int((time.perf_counter() - started) * 1000)
        if on_progress:
            on_progress(run)
        return run

    # --- execution ---

    def _step(self, node: WorkflowNode, run: WorkflowRun) -> WorkflowStepResult:
        step = WorkflowStepResult(
            node_id=node.id,
            label=node_label(node),
            type=node.type,
            status=WorkflowStepStatus.RUNNING,
            input=self._block_input(flow_node=node, inputs=run.inputs),
        )
        if not node.enabled:
            step.status = WorkflowStepStatus.SKIPPED
            step.error = "Block is disabled."
            return step

        started = time.perf_counter()
        try:
            output = self._execute(node, run)
        except (WorkflowBlockedError, WorkflowOrderError) as exc:
            step.status = (
                WorkflowStepStatus.BLOCKED
                if isinstance(exc, WorkflowBlockedError)
                else WorkflowStepStatus.FAILED
            )
            step.error = str(exc)
        # A failed step is surfaced in the monitor, not raised at the caller.
        except Exception as exc:  # noqa: BLE001
            step.status = WorkflowStepStatus.FAILED
            step.error = str(exc)
        else:
            step.status = WorkflowStepStatus.OK
            step.output = output
            run.outputs.update(
                {f"{node.id}.{key}": value for key, value in output.items()}
            )
        step.duration_ms = int((time.perf_counter() - started) * 1000)
        return step

    @staticmethod
    def _block_input(flow_node: WorkflowNode, inputs: dict[str, Any]) -> dict[str, Any]:
        """Parameters plus the variables the operator supplied for the run."""
        merged: dict[str, Any] = dict(flow_node.params)
        for key, value in inputs.items():
            if not key.startswith(flow_node.id):
                merged.setdefault(key, value)
        return merged

    def _execute(self, node: WorkflowNode, run: WorkflowRun) -> dict[str, Any]:
        project = self._service.get_project(run.project_id)
        params = node.params
        inputs = run.inputs

        if node.type == WorkflowNodeType.RESEARCH:
            include_web = bool(params.get("include_web", True))
            _run_sync(self._service.research(run.project_id, include_web=include_web))
            research = self._service.get_project(run.project_id).research
            return {
                "sources": len(research.sources) if research else 0,
                "key_facts": len(research.key_facts) if research else 0,
            }

        if node.type == WorkflowNodeType.SCRIPT:
            supplied = str(inputs.get("script") or "").strip()
            if supplied:
                # An operator (or an external agent) handed us a script: adopt
                # it instead of drafting a competing one.
                return {"source": "input", "characters": len(supplied)}
            if project.script and project.status not in (
                ProjectStatus.DRAFT,
                ProjectStatus.SCRIPT_REVIEW,
            ):
                # Never redraft behind an approval that already happened.
                return {
                    "source": "existing",
                    "characters": len(project.script),
                    "status": project.status.value,
                }
            project = _run_sync(self._service.generate_script(run.project_id))
            return {
                "source": "draft",
                "provider": project.provider_used or "unknown",
                "characters": len(project.script or ""),
                "status": project.status.value,
            }

        if node.type == WorkflowNodeType.LINT:
            target = str(inputs.get("script") or project.script or "")
            analysis = self._service.analyze_project_script(
                run.project_id, ScriptAnalyzeRequest(script=target)
            )
            return {
                "score": analysis.score,
                "issues": [issue.code for issue in analysis.issues],
                "estimated_seconds": analysis.plan.estimated_seconds,
                "fits_target": analysis.plan.fits_target,
            }

        if node.type == WorkflowNodeType.GATE:
            stage = ApprovalStage(
                str(params.get("stage") or ApprovalStage.SCRIPT.value)
            )
            return self._check_gate(run.project_id, stage)

        if node.type == WorkflowNodeType.SCENES:
            existing = project.video_project
            if existing is not None and project.status in _PRODUCED_STATUSES:
                # Rebuilding would silently discard hand-made edits.
                return {"scenes": len(existing.scenes), "rebuilt": False}
            produced = self._service.produce_video(run.project_id)
            timeline = produced.video_project
            return {
                "scenes": len(timeline.scenes) if timeline else 0,
                "rebuilt": True,
                "status": produced.status.value,
            }

        if node.type == WorkflowNodeType.VOICEOVER:
            if project.video_project is None:
                raise WorkflowOrderError(
                    "Narration needs a timeline: put a 'Produce video' block "
                    "before this one."
                )
            narrated = self._service.synthesize_voiceover(run.project_id)
            bundle = narrated.voiceover
            if bundle is None or not bundle.tracks:
                raise WorkflowOrderError(
                    "No narration was produced. Check the text-to-speech "
                    "settings and that the scenes have text."
                )
            return {"engine": bundle.engine, "tracks": len(bundle.tracks)}

        if node.type == WorkflowNodeType.AI_ASSIST:
            project = self._service.apply_ai_assist(
                run.project_id,
                fit=bool(params.get("fit", True)),
                beat=bool(params.get("beat", False)),
                bpm=int(params.get("bpm", 120) or 120),
            )
            timeline = project.video_project
            total = (
                sum(scene.duration_seconds for scene in timeline.scenes)
                if timeline
                else 0.0
            )
            return {
                "scenes": len(timeline.scenes) if timeline else 0,
                "total_seconds": round(total, 2),
            }

        if node.type == WorkflowNodeType.TIMELINE_CHECK:
            report = self._service.timeline_report(run.project_id)
            return {
                "score": report.score,
                "issues": [issue.code for issue in report.issues],
                "total_seconds": report.stats.total_seconds,
            }

        if node.type == WorkflowNodeType.RENDER_PLAN:
            plan = self._service.render_plan(run.project_id)
            return {
                "total_seconds": plan.total_seconds,
                "steps": len(plan.steps),
                "caption_cues": len(plan.subtitles),
                "warnings": plan.warnings,
            }

        if node.type == WorkflowNodeType.PUBLISH:
            platforms = params.get("platforms") or ["youtube"]
            if isinstance(platforms, str):
                platforms = [
                    item.strip() for item in platforms.split(",") if item.strip()
                ]
            project = self._service.get_project(run.project_id)
            if project.status == ProjectStatus.VIDEO_REVIEW:
                raise WorkflowBlockedError(
                    "Waiting for the final video approval (Gate 2) before publishing."
                )
            published = self._service.publish(
                run.project_id, PublishCreate(platforms=list(platforms))
            )
            return {"platforms": published.platforms, "status": published.status.value}

        if node.type == WorkflowNodeType.INGEST_EXTERNAL:
            assets_payload = inputs.get("external_assets")
            if assets_payload and isinstance(assets_payload, list):
                from .models import ExternalImportRequest

                reqs = [
                    ExternalImportRequest.model_validate(item)
                    for item in assets_payload
                ]
                self._service.batch_import_external_assets(run.project_id, reqs)
                project = self._service.get_project(run.project_id)
            attached = len(project.external_assets)
            scenes_with_media = 0
            if project.video_project:
                scenes_with_media = sum(
                    1
                    for s in project.video_project.scenes
                    if s.image_url or s.video_url
                )
            return {
                "external_assets_count": attached,
                "scenes_with_media": scenes_with_media,
                "music_attached": bool(
                    project.video_project and project.video_project.background_music_url
                ),
            }

        raise ValueError(f"Unknown block type '{node.type}'.")

    def _check_gate(self, project_id: str, stage: ApprovalStage) -> dict[str, Any]:
        """Verify a human gate is passed; block the run when it is not."""
        project = self._service.get_project(project_id)
        status = project.status
        if stage == ApprovalStage.SCRIPT:
            if status == ProjectStatus.SCRIPT_REVIEW:
                raise WorkflowBlockedError(
                    "Waiting for the script approval (Gate 1). Approve the script "
                    "in the review gate, then run the flow again."
                )
            passed_past_gate = status in (
                ProjectStatus.SCRIPT_APPROVED,
                ProjectStatus.GENERATING,
                ProjectStatus.VIDEO_REVIEW,
                ProjectStatus.VIDEO_APPROVED,
                ProjectStatus.PUBLISHED,
            )
            if not passed_past_gate:
                raise WorkflowBlockedError(
                    f"The script gate cannot be evaluated while status is "
                    f"'{status.value}'. Approve the script first."
                )
            approvals = [
                record
                for record in project.approvals
                if record.stage == ApprovalStage.SCRIPT
                and record.verdict.value == "approved"
            ]
            return {
                "gate": stage.value,
                "passed": True,
                "approved_at": approvals[-1].created_at.isoformat()
                if approvals
                else None,
            }

        if status == ProjectStatus.VIDEO_REVIEW:
            raise WorkflowBlockedError(
                "Waiting for the final video approval (Gate 2). Review the exported "
                "video, then run the flow again."
            )
        if status != ProjectStatus.VIDEO_APPROVED:
            raise WorkflowBlockedError(
                f"The video gate cannot be evaluated while status is '{status.value}'."
            )
        return {"gate": stage.value, "passed": True, "approved_status": status.value}


def describe_blocks() -> list[dict[str, Any]]:
    """The block palette: every type with its label, description, and params."""
    return [
        {
            "type": node_type.value,
            "label": NODE_LABELS[node_type],
            "description": NODE_DESCRIPTIONS[node_type],
            "params": list(REQUIRED_PARAMS.get(node_type, ())),
            "default_params": _default_params(node_type),
            "icon": _ICONS[node_type],
        }
        for node_type in WorkflowNodeType
    ]


_ICONS: dict[WorkflowNodeType, str] = {
    WorkflowNodeType.RESEARCH: "🔬",
    WorkflowNodeType.SCRIPT: "📝",
    WorkflowNodeType.LINT: "🔍",
    WorkflowNodeType.GATE: "🛡",
    WorkflowNodeType.VOICEOVER: "🎙",
    WorkflowNodeType.SCENES: "🎞",
    WorkflowNodeType.AI_ASSIST: "✨",
    WorkflowNodeType.TIMELINE_CHECK: "🩺",
    WorkflowNodeType.RENDER_PLAN: "📋",
    WorkflowNodeType.PUBLISH: "📢",
    WorkflowNodeType.INGEST_EXTERNAL: "📥",
}


def _default_params(node_type: WorkflowNodeType) -> dict[str, Any]:
    if node_type == WorkflowNodeType.GATE:
        return {"stage": ApprovalStage.SCRIPT.value}
    if node_type == WorkflowNodeType.PUBLISH:
        return {"platforms": ["youtube"]}
    if node_type == WorkflowNodeType.RESEARCH:
        return {"include_web": True}
    if node_type == WorkflowNodeType.AI_ASSIST:
        return {"fit": True, "beat": False, "bpm": 120}
    return {}


def project_flow(project: Project) -> Workflow:
    """The project's own flow, or a fresh copy of the default one."""
    if project.workflow is None:
        return default_workflow()
    return normalize_workflow(project.workflow.model_copy(deep=True))
