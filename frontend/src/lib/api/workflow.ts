/**
 * Workflow DAG endpoints: the palette, the saved flow, the pre-save gate and runs.
 *
 * Two payload rules the studio used to get wrong and that are encoded here:
 *
 * * the pre-save gate and the save both take ``WorkflowSave`` — the flow nested
 *   under ``workflow`` — not a bare ``{nodes, edges}``;
 * * ``background`` is a **query parameter** on the run route, not part of the body.
 */

import * as api from "@/lib/api/client";
import { Project } from "@/types/project";
import {
  Workflow,
  WorkflowBlockDef,
  WorkflowChecklist,
  WorkflowRun,
} from "@/types/workflow";

/** ``GET /workflow/blocks`` — every block type the canvas can offer. */
export function listBlocks(): Promise<WorkflowBlockDef[]> {
  return api.apiFetch<WorkflowBlockDef[]>("/workflow/blocks");
}

/** ``GET /projects/{id}/workflow`` — the saved flow. */
export function getWorkflow(projectId: string): Promise<Workflow> {
  return api.apiFetch<Workflow>(`/projects/${projectId}/workflow`);
}

/** ``GET /projects/{id}/workflow/checklist`` — the saved flow, audited. */
export function checkChecklist(projectId: string): Promise<WorkflowChecklist> {
  return api.apiFetch<WorkflowChecklist>(
    `/projects/${projectId}/workflow/checklist`
  );
}

/**
 * ``POST /projects/{id}/workflow/checklist`` — audit a *candidate* flow.
 *
 * Used while the operator is editing, so the checklist describes what is on the
 * canvas rather than the last saved version.
 */
export function validateChecklist(
  projectId: string,
  workflow: Workflow,
  force = false
): Promise<WorkflowChecklist> {
  return api.apiFetch<WorkflowChecklist>(
    `/projects/${projectId}/workflow/checklist`,
    { method: "POST", body: { workflow, force } }
  );
}

/** ``PUT /projects/{id}/workflow`` — save the flow onto the project. */
export function saveWorkflow(
  projectId: string,
  workflow: Workflow,
  force = false
): Promise<Project> {
  return api.apiFetch<Project>(`/projects/${projectId}/workflow`, {
    method: "PUT",
    body: { workflow, force },
  });
}

/**
 * ``POST /projects/{id}/workflow/run``.
 *
 * ``background=true`` returns as soon as the run is queued; the synchronous path
 * runs the flow in a worker thread and can take as long as the pipeline does.
 */
export function runWorkflow(
  projectId: string,
  inputs: Record<string, unknown> = {},
  background = false
): Promise<WorkflowRun> {
  return api.apiFetch<WorkflowRun>(`/projects/${projectId}/workflow/run`, {
    method: "POST",
    query: { background },
    body: { inputs },
  });
}

/** ``GET /projects/{id}/workflow/runs`` — the run history. */
export function listRuns(projectId: string): Promise<WorkflowRun[]> {
  return api.apiFetch<WorkflowRun[]>(`/projects/${projectId}/workflow/runs`);
}

/** ``GET /workflow/runs/{run_id}`` — one run, by id. */
export function getRun(runId: string): Promise<WorkflowRun> {
  return api.apiFetch<WorkflowRun>(`/workflow/runs/${runId}`);
}
