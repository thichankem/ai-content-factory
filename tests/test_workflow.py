"""Tests for the drag-and-drop production flows."""

from __future__ import annotations

import time

import pytest

from content_factory import workflow
from content_factory.config import Settings
from content_factory.models import (
    ApprovalCreate,
    IssueSeverity,
    ProjectCreate,
    ProjectStatus,
    ScriptUpdate,
    Workflow,
    WorkflowEdge,
    WorkflowNode,
    WorkflowNodeType,
    WorkflowRunRequest,
    WorkflowRunStatus,
    WorkflowSave,
    WorkflowStepStatus,
)
from content_factory.service import ContentFactoryService
from content_factory.workflow import WorkflowChecklistError, WorkflowRunner

SCRIPT = (
    "[Hook]\nThe library at midnight has a sound of its own.\n\n"
    "[Turn]\nPages breathe, chairs settle, the clock keeps score.\n\n"
    "[Payoff]\nStay past closing and the building starts talking."
)


@pytest.fixture
def template_service(settings: Settings) -> ContentFactoryService:
    """A service whose only provider is the offline built-in template."""
    return ContentFactoryService(settings.model_copy(update={"template_enabled": True}))


def _chain(*types: WorkflowNodeType, **params: dict) -> Workflow:
    """A straight-line flow with one block per type, laid out left to right."""
    nodes = [
        WorkflowNode(
            id=f"n{index + 1}",
            type=node_type,
            label=workflow.NODE_LABELS[node_type],
            x=40.0 + index * 210.0,
            y=180.0,
            params=params.get(node_type.value, {}),
        )
        for index, node_type in enumerate(types)
    ]
    edges = [
        WorkflowEdge(id=f"e{index}", source=nodes[index - 1].id, target=nodes[index].id)
        for index in range(1, len(nodes))
    ]
    return Workflow(nodes=nodes, edges=edges)


# --- the default flow ---------------------------------------------------------


def test_default_flow_is_ready_to_run() -> None:
    flow = workflow.default_workflow()
    assert [node.type for node in flow.nodes] == [
        WorkflowNodeType.RESEARCH,
        WorkflowNodeType.SCRIPT,
        WorkflowNodeType.LINT,
        WorkflowNodeType.GATE,
        WorkflowNodeType.SCENES,
        WorkflowNodeType.VOICEOVER,
        WorkflowNodeType.AI_ASSIST,
        WorkflowNodeType.TIMELINE_CHECK,
        WorkflowNodeType.RENDER_PLAN,
    ]
    assert len(flow.edges) == len(flow.nodes) - 1
    result = workflow.checklist(flow)
    assert result.ready is True
    assert [issue.code for issue in result.issues] == []
    assert result.order == [node.id for node in flow.nodes]


def test_default_flow_produces_before_it_narrates() -> None:
    """A block may only consume what an earlier block has produced."""
    order = [node.type for node in workflow.default_workflow().nodes]
    assert order.index(WorkflowNodeType.SCENES) < order.index(
        WorkflowNodeType.VOICEOVER
    )


def test_block_catalog_covers_every_type() -> None:
    catalog = workflow.describe_blocks()
    assert {entry["type"] for entry in catalog} == {
        node_type.value for node_type in WorkflowNodeType
    }
    assert all(entry["label"] and entry["description"] for entry in catalog)
    gate = next(entry for entry in catalog if entry["type"] == "gate")
    assert gate["params"] == ["stage"]
    assert gate["default_params"] == {"stage": "script"}


# --- normalizing a dragged-around canvas --------------------------------------


def test_normalize_drops_links_to_deleted_blocks() -> None:
    flow = workflow.default_workflow()
    victim = flow.nodes[-1].id
    flow.nodes = [node for node in flow.nodes if node.id != victim]
    repaired = workflow.normalize_workflow(flow)
    assert all(edge.target != victim for edge in repaired.edges)
    assert len(repaired.edges) == len(repaired.nodes) - 1


def test_normalize_repairs_duplicate_ids_and_self_links() -> None:
    flow = Workflow(
        nodes=[
            WorkflowNode(id="dup", type=WorkflowNodeType.RESEARCH),
            WorkflowNode(id="dup", type=WorkflowNodeType.SCRIPT),
            WorkflowNode(id="", type=WorkflowNodeType.LINT),
        ],
        edges=[
            WorkflowEdge(id="a", source="dup", target="dup"),
            WorkflowEdge(id="b", source="dup", target="dup"),
        ],
    )
    flow.nodes.append(WorkflowNode(id="third", type=WorkflowNodeType.LINT))
    flow.edges.extend(
        [
            WorkflowEdge(id="c", source="dup", target="third"),
            WorkflowEdge(id="d", source="dup", target="third"),
        ]
    )
    repaired = workflow.normalize_workflow(flow)
    ids = [node.id for node in repaired.nodes]
    assert len(set(ids)) == len(ids) == 4
    assert all(edge.source != edge.target for edge in repaired.edges)
    # The self-links go, the duplicate of the same link goes, one survives.
    assert len(repaired.edges) == 1


def test_normalize_is_idempotent() -> None:
    flow = workflow.default_workflow()
    once = workflow.normalize_workflow(flow)
    twice = workflow.normalize_workflow(once.model_copy(deep=True))
    assert once.model_dump() == twice.model_dump()


# --- ordering and the checklist ----------------------------------------------


def test_order_is_stable_and_respects_links() -> None:
    flow = _chain(
        WorkflowNodeType.RESEARCH, WorkflowNodeType.SCRIPT, WorkflowNodeType.LINT
    )
    first, _ = workflow.topological_order(flow)
    second, _ = workflow.topological_order(flow)
    assert first == second == [node.id for node in flow.nodes]


def test_order_reports_the_blocks_inside_a_loop() -> None:
    flow = _chain(WorkflowNodeType.RESEARCH, WorkflowNodeType.SCRIPT)
    flow.edges.append(WorkflowEdge(id="loop", source="n2", target="n1"))
    order, cyclic = workflow.topological_order(flow)
    assert order == []
    assert cyclic == ["n1", "n2"]

    result = workflow.checklist(flow)
    assert result.ready is False
    assert "cycle" in {issue.code for issue in result.issues}


def test_checklist_flags_unfinished_and_unwired_blocks() -> None:
    flow = Workflow(
        nodes=[
            WorkflowNode(id="n1", type=WorkflowNodeType.RESEARCH, label=""),
            WorkflowNode(
                id="n2", type=WorkflowNodeType.GATE, label="Review", params={}
            ),
            WorkflowNode(
                id="n3",
                type=WorkflowNodeType.GATE,
                label="Review",
                params={"stage": "nonsense"},
            ),
            WorkflowNode(id="n4", type=WorkflowNodeType.PUBLISH, label="Ship"),
        ],
        edges=[WorkflowEdge(id="e1", source="n1", target="n2")],
    )
    codes = [issue.code for issue in workflow.checklist(flow).issues]
    assert codes.count("unnamed_block") == 1
    assert codes.count("missing_param") == 2
    assert "invalid_param" in codes
    assert "unconnected_block" in codes


def test_checklist_asks_for_a_review_gate() -> None:
    flow = _chain(WorkflowNodeType.SCRIPT, WorkflowNodeType.LINT)
    issue = next(
        item
        for item in workflow.checklist(flow).issues
        if item.code == "missing_script_gate"
    )
    assert issue.severity == IssueSeverity.WARNING
    assert "gate" in (issue.hint or "")


def test_checklist_rejects_an_empty_canvas() -> None:
    result = workflow.checklist(Workflow())
    assert result.ready is False
    assert [issue.code for issue in result.issues] == ["empty_flow"]


# --- saving a flow through the service ---------------------------------------


def test_save_workflow_versions_and_persists(service: ContentFactoryService) -> None:
    project = service.create_project(
        ProjectCreate(name="Flow", topic="A topic", duration_target_seconds=30)
    )
    assert project.workflow is None
    saved = service.save_workflow(
        project.id, WorkflowSave(workflow=workflow.default_workflow())
    )
    assert saved.workflow is not None
    assert saved.workflow.version == 1
    again = service.save_workflow(saved.id, WorkflowSave(workflow=saved.workflow))
    assert again.workflow is not None
    assert again.workflow.version == 2
    assert service.project_workflow(project.id).nodes


def test_save_workflow_refuses_an_unfinished_flow(
    service: ContentFactoryService,
) -> None:
    project = service.create_project(
        ProjectCreate(name="Flow", topic="A topic", duration_target_seconds=30)
    )
    broken = Workflow(
        nodes=[WorkflowNode(id="n1", type=WorkflowNodeType.GATE, label="", params={})],
        edges=[],
    )
    with pytest.raises(WorkflowChecklistError) as caught:
        service.save_workflow(project.id, WorkflowSave(workflow=broken))
    assert caught.value.checklist.ready is False
    assert "gate" in str(caught.value)


def test_save_workflow_can_be_forced(service: ContentFactoryService) -> None:
    project = service.create_project(
        ProjectCreate(name="Flow", topic="A topic", duration_target_seconds=30)
    )
    draft = Workflow(
        nodes=[
            WorkflowNode(id="n1", type=WorkflowNodeType.RESEARCH, label="", params={})
        ],
        edges=[],
    )
    saved = service.save_workflow(project.id, WorkflowSave(workflow=draft, force=True))
    assert saved.workflow is not None
    assert len(saved.workflow.nodes) == 1


# --- running a flow ----------------------------------------------------------


def _approve_script(service: ContentFactoryService, project_id: str) -> None:
    service.update_script(
        project_id, ScriptUpdate(script=SCRIPT, source_rights_confirmed=True)
    )
    service.approve(project_id, ApprovalCreate(stage="script", verdict="approved"))


def test_run_stops_at_the_first_human_gate(
    template_service: ContentFactoryService,
) -> None:
    service = template_service
    project = service.create_project(
        ProjectCreate(
            name="Gated",
            topic="A library at midnight",
            target_language="en",
            duration_target_seconds=30,
        )
    )
    run = service.run_workflow(project.id, WorkflowRunRequest())
    assert run.status == WorkflowRunStatus.BLOCKED
    assert [step.type for step in run.steps] == [
        WorkflowNodeType.RESEARCH,
        WorkflowNodeType.SCRIPT,
        WorkflowNodeType.LINT,
        WorkflowNodeType.GATE,
    ]
    assert run.steps[-1].status == WorkflowStepStatus.BLOCKED
    assert "Gate 1" in (run.steps[-1].error or "")
    # Nothing after the gate was attempted, and nothing was auto-approved.
    assert service.get_project(project.id).status == ProjectStatus.SCRIPT_REVIEW
    assert run.steps[1].output["source"] == "draft"


def test_run_resumes_after_the_gate_was_passed(
    template_service: ContentFactoryService,
) -> None:
    service = template_service
    project = service.create_project(
        ProjectCreate(
            name="Resumed",
            topic="A library at midnight",
            target_language="en",
            duration_target_seconds=30,
        )
    )
    _approve_script(service, project.id)
    run = service.run_workflow(project.id, WorkflowRunRequest())
    types = [step.type for step in run.steps]
    assert types[:4] == [
        WorkflowNodeType.RESEARCH,
        WorkflowNodeType.SCRIPT,
        WorkflowNodeType.LINT,
        WorkflowNodeType.GATE,
    ]
    assert run.steps[1].output["source"] == "existing"
    assert service.get_project(project.id).script == SCRIPT
    # Narration needs a timeline, so production must come before it.
    scened = next(step for step in run.steps if step.type == WorkflowNodeType.SCENES)
    assert scened.output["rebuilt"] is True


def test_run_reaches_the_render_plan_when_tts_is_off(
    template_service: ContentFactoryService,
) -> None:
    service = template_service
    project = service.create_project(
        ProjectCreate(
            name="No narration",
            topic="A library at midnight",
            target_language="en",
            duration_target_seconds=30,
        )
    )
    _approve_script(service, project.id)
    flow = _chain(
        WorkflowNodeType.SCENES,
        WorkflowNodeType.AI_ASSIST,
        WorkflowNodeType.TIMELINE_CHECK,
        WorkflowNodeType.RENDER_PLAN,
    )
    service.save_workflow(project.id, WorkflowSave(workflow=flow))
    run = service.run_workflow(project.id, WorkflowRunRequest())
    assert run.status == WorkflowRunStatus.OK
    plan_step = run.steps[-1]
    assert plan_step.output["steps"] > 0
    assert plan_step.output["caption_cues"] >= 1
    assert service.get_project(project.id).status == ProjectStatus.VIDEO_REVIEW


def test_narrating_without_a_timeline_fails_loudly(
    template_service: ContentFactoryService,
) -> None:
    """A flow that narrates before producing anything must fail, not drift."""
    service = template_service
    project = service.create_project(
        ProjectCreate(name="Wrong order", topic="A topic", duration_target_seconds=30)
    )
    flow = _chain(WorkflowNodeType.VOICEOVER)
    service.save_workflow(project.id, WorkflowSave(workflow=flow, force=True))
    run = service.run_workflow(project.id, WorkflowRunRequest())
    assert run.status == WorkflowRunStatus.FAILED
    assert run.steps[0].status == WorkflowStepStatus.FAILED
    assert "timeline" in (run.steps[0].error or "")


def test_narrating_with_tts_disabled_halts_the_run(settings: Settings) -> None:
    service = ContentFactoryService(
        settings.model_copy(
            update={"template_enabled": True, "tts_enabled": False, "tts_engine": "off"}
        )
    )
    project = service.create_project(
        ProjectCreate(
            name="Muted",
            topic="A library at midnight",
            target_language="en",
            duration_target_seconds=30,
        )
    )
    _approve_script(service, project.id)
    flow = _chain(WorkflowNodeType.SCENES, WorkflowNodeType.VOICEOVER)
    service.save_workflow(project.id, WorkflowSave(workflow=flow))
    run = service.run_workflow(project.id, WorkflowRunRequest())
    assert run.status == WorkflowRunStatus.FAILED
    assert run.steps[0].status == WorkflowStepStatus.OK
    assert run.steps[1].type == WorkflowNodeType.VOICEOVER
    assert "disabled" in (run.steps[1].error or "")


def test_rebuilding_scenes_never_wipes_the_timeline(
    template_service: ContentFactoryService,
) -> None:
    service = template_service
    project = service.create_project(
        ProjectCreate(
            name="Kept",
            topic="A library at midnight",
            target_language="en",
            duration_target_seconds=30,
        )
    )
    _approve_script(service, project.id)
    service.produce_video(project.id)
    timeline = service.get_project(project.id).video_project
    assert timeline is not None
    timeline.scenes[0].label = "Hand-written hook"
    service.update_video_project(project.id, timeline)

    flow = _chain(WorkflowNodeType.SCENES)
    service.save_workflow(project.id, WorkflowSave(workflow=flow, force=True))
    run = service.run_workflow(project.id, WorkflowRunRequest())
    assert run.steps[0].output["rebuilt"] is False
    kept = service.get_project(project.id).video_project
    assert kept is not None
    assert kept.scenes[0].label == "Hand-written hook"


def test_progress_is_published_block_by_block(
    template_service: ContentFactoryService,
) -> None:
    """A monitor must see the run grow, not just its final state."""
    service = template_service
    project = service.create_project(
        ProjectCreate(
            name="Monitored",
            topic="A library at midnight",
            target_language="en",
            duration_target_seconds=30,
        )
    )
    _approve_script(service, project.id)
    flow = _chain(
        WorkflowNodeType.SCENES,
        WorkflowNodeType.TIMELINE_CHECK,
        WorkflowNodeType.RENDER_PLAN,
    )
    service.save_workflow(project.id, WorkflowSave(workflow=flow))

    snapshots: list[list[str]] = []
    runner = WorkflowRunner(service)
    run = runner.run(
        project.id,
        workflow=flow,
        on_progress=lambda partial: snapshots.append(
            [step.status.value for step in partial.steps]
        ),
    )
    assert run.status == WorkflowRunStatus.OK
    # The first snapshot is the empty run, then one more per finished block.
    assert snapshots[0] == []
    assert [len(item) for item in snapshots] == [0, 1, 2, 3, 3]
    assert snapshots[1][0] in {"ok", "running"}


def test_background_run_streams_into_the_run_record(
    template_service: ContentFactoryService,
) -> None:
    service = template_service
    project = service.create_project(
        ProjectCreate(
            name="Streamed",
            topic="A library at midnight",
            target_language="en",
            duration_target_seconds=30,
        )
    )
    _approve_script(service, project.id)
    flow = _chain(WorkflowNodeType.SCENES, WorkflowNodeType.RENDER_PLAN)
    service.save_workflow(project.id, WorkflowSave(workflow=flow))

    started = service.start_workflow(project.id, WorkflowRunRequest())
    assert started.status == WorkflowRunStatus.RUNNING
    finished = None
    for _ in range(400):
        current = service.workflow_run(started.id)
        if current.status != WorkflowRunStatus.RUNNING:
            finished = current
            break
        time.sleep(0.02)
    assert finished is not None, "the background run never finished"
    assert finished.id == started.id
    assert finished.status == WorkflowRunStatus.OK
    assert [step.type for step in finished.steps] == [
        WorkflowNodeType.SCENES,
        WorkflowNodeType.RENDER_PLAN,
    ]
    assert service.workflow_runs(project.id)[0].id == started.id


def test_unknown_block_type_fails_the_block_not_the_server() -> None:
    class _Recording:
        pass

    runner = WorkflowRunner(_Recording())  # type: ignore[arg-type]
    flow = _chain(WorkflowNodeType.RESEARCH)
    flow.nodes[0].type = WorkflowNodeType.AI_ASSIST  # needs a service method
    run = runner.run("missing-project", workflow=flow)
    assert run.status == WorkflowRunStatus.FAILED
    assert run.steps[0].status == WorkflowStepStatus.FAILED


def test_run_records_timing_and_tracks_inputs(
    template_service: ContentFactoryService,
) -> None:
    service = template_service
    project = service.create_project(
        ProjectCreate(
            name="Inputs",
            topic="A library at midnight",
            target_language="en",
            duration_target_seconds=30,
        )
    )
    _approve_script(service, project.id)
    flow = _chain(WorkflowNodeType.LINT)
    service.save_workflow(project.id, WorkflowSave(workflow=flow, force=True))
    run = service.run_workflow(
        project.id, WorkflowRunRequest(inputs={"script": SCRIPT})
    )
    assert run.inputs == {"script": SCRIPT}
    assert run.duration_ms >= 0
    assert run.finished_at is not None
    assert run.id
    assert service.workflow_runs(project.id)[0].id == run.id
    assert service.workflow_run(run.id).id == run.id
