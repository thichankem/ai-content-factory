import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchApi } from "../lib/api-client";
import { Project } from "../types/project";

export interface WorkflowBlockDef {
  type: string;
  name: string;
  category: "input" | "process" | "gate" | "output" | "ingest";
  description: string;
  inputs: string[];
  outputs: string[];
  default_config: Record<string, any>;
}

export interface WorkflowNode {
  id: string;
  block_type: string;
  name: string;
  x: number;
  y: number;
  config: Record<string, any>;
  inputs?: string[];
  outputs?: string[];
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  source_handle?: string;
  target_handle?: string;
}

export interface WorkflowData {
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
}

export interface WorkflowChecklistResult {
  ready: boolean;
  issues: Array<{ severity: "error" | "warning" | "info"; message: string; node_id?: string }>;
  cycles_detected: boolean;
  has_gate_1: boolean;
  has_gate_2: boolean;
}

export interface WorkflowRunResult {
  run_id: string;
  project_id: string;
  status: "completed" | "failed" | "running";
  executed_blocks: Array<{
    node_id: string;
    block_type: string;
    status: "ok" | "skipped" | "error";
    duration_ms: number;
    log: string;
  }>;
  error?: string;
}

export function useWorkflowDAG(projectId?: string) {
  const queryClient = useQueryClient();

  const blocksQuery = useQuery({
    queryKey: ["workflow-blocks"],
    queryFn: () => fetchApi<WorkflowBlockDef[]>("/workflow/blocks"),
    staleTime: 1000 * 60 * 60,
  });

  const workflowQuery = useQuery({
    queryKey: ["project-workflow", projectId],
    queryFn: () => {
      if (!projectId) return null;
      return fetchApi<WorkflowData>(`/projects/${projectId}/workflow`);
    },
    enabled: !!projectId,
  });

  const checklistQuery = useQuery({
    queryKey: ["workflow-checklist", projectId],
    queryFn: () => {
      if (!projectId) return null;
      return fetchApi<WorkflowChecklistResult>(`/projects/${projectId}/workflow/checklist`);
    },
    enabled: !!projectId,
  });

  const validateChecklistMutation = useMutation({
    mutationFn: (data: WorkflowData) => {
      if (!projectId) throw new Error("No project selected");
      return fetchApi<WorkflowChecklistResult>(`/projects/${projectId}/workflow/checklist`, {
        method: "POST",
        body: JSON.stringify(data),
      });
    },
  });

  const saveWorkflowMutation = useMutation({
    mutationFn: (data: WorkflowData) => {
      if (!projectId) throw new Error("No project selected");
      return fetchApi<Project>(`/projects/${projectId}/workflow`, {
        method: "PUT",
        body: JSON.stringify(data),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project-workflow", projectId] });
      queryClient.invalidateQueries({ queryKey: ["workflow-checklist", projectId] });
    },
  });

  const runWorkflowMutation = useMutation({
    mutationFn: (data?: { inputs?: Record<string, any>; background?: boolean }) => {
      if (!projectId) throw new Error("No project selected");
      return fetchApi<WorkflowRunResult>(`/projects/${projectId}/workflow/run`, {
        method: "POST",
        body: JSON.stringify(data || {}),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workflow-runs", projectId] });
      queryClient.invalidateQueries({ queryKey: ["projects", projectId] });
    },
  });

  const runsQuery = useQuery({
    queryKey: ["workflow-runs", projectId],
    queryFn: () => {
      if (!projectId) return [];
      return fetchApi<WorkflowRunResult[]>(`/projects/${projectId}/workflow/runs`);
    },
    enabled: !!projectId,
  });

  return {
    blocksQuery,
    workflowQuery,
    checklistQuery,
    validateChecklistMutation,
    saveWorkflowMutation,
    runWorkflowMutation,
    runsQuery,
  };
}
