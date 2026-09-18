/**
 * Workflow DAG contract — mirrors ``models/workflow.py`` and
 * ``workflow.describe_blocks()``.
 *
 * ### Field names that used to be wrong
 *
 * A node carries ``type``/``label``/``params``; the old client types called the
 * same things ``block_type``/``name``/``config``, so the canvas rendered blank
 * labels and an editor that wrote ``config`` was rejected. The palette ships
 * ``params`` as a list of required parameter *names* plus ``default_params``.
 */

import { IssueSeverity } from "@/types/common";
import { ApprovalStage } from "@/types/common";

/** The kinds of block a production flow can contain. */
export type WorkflowNodeType =
  | "research"
  | "script"
  | "lint"
  | "gate"
  | "voiceover"
  | "scenes"
  | "ai_assist"
  | "timeline_check"
  | "render_plan"
  | "publish"
  | "ingest_external";

/** One draggable block in the flow canvas. */
export interface WorkflowNode {
  id: string;
  type: WorkflowNodeType;
  label: string;
  x: number;
  y: number;
  enabled: boolean;
  params: Record<string, unknown>;
}

/** A directed link between two blocks. */
export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
}

/** A production flow (`Workflow`). */
export interface Workflow {
  name: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  version: number;
  updated_at: string;
}

/** One pre-save finding. */
export interface WorkflowCheckIssue {
  code: string;
  severity: IssueSeverity;
  message: string;
  hint?: string | null;
  node_id?: string | null;
}

/** The pre-save gate's verdict (`WorkflowChecklist`). */
export interface WorkflowChecklist {
  issues: WorkflowCheckIssue[];
  ready: boolean;
  node_count: number;
  edge_count: number;
  order: string[];
}

/** Payload for ``PUT /projects/{id}/workflow`` and the checklist POST. */
export interface WorkflowSave {
  workflow: Workflow;
  force?: boolean;
}

/** Payload for ``POST /projects/{id}/workflow/run`` (`WorkflowRunRequest`). */
export interface WorkflowRunRequest {
  inputs?: Record<string, unknown>;
}

/** Lifecycle of a flow run. */
export type WorkflowRunStatus = "running" | "completed" | "failed";

/** Lifecycle of one executed block. */
export type WorkflowStepStatus = "pending" | "running" | "succeeded" | "failed" | "skipped";

/** One executed block of a run (`WorkflowStepResult`). */
export interface WorkflowStepResult {
  node_id: string;
  label: string;
  type: WorkflowNodeType;
  status: WorkflowStepStatus;
  duration_ms: number;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  error?: string | null;
}

/** A flow run (`WorkflowRun`). */
export interface WorkflowRun {
  id: string;
  project_id: string;
  status: WorkflowRunStatus;
  inputs: Record<string, unknown>;
  outputs: Record<string, unknown>;
  steps: WorkflowStepResult[];
  message?: string | null;
  started_at: string;
  finished_at?: string | null;
  duration_ms: number;
}

/**
 * One entry of the block palette (``GET /workflow/blocks``).
 *
 * ``params`` is the list of *required* parameter names for the block; the values
 * they start with live in ``default_params``.
 */
export interface WorkflowBlockDef {
  type: WorkflowNodeType;
  label: string;
  description: string;
  params: string[];
  default_params: Record<string, unknown>;
  icon: string;
}

/** A gate block's parameters. */
export interface GateParams {
  stage: ApprovalStage;
}
