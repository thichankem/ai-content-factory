/**
 * Workflow DAG hooks.
 *
 * Everything here talks about a flow that the *backend* owns: the palette, the
 * saved flow, the pre-save gate and runs. Two contract details are load-bearing:
 *
 * * a node carries ``type``/``label``/``params`` (not ``block_type``/``name``/
 *   ``config``), so a canvas that writes the old names is rejected;
 * * the checklist and the save both wrap the flow in ``{workflow, force}``.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { workflowApi } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { syncProject } from "@/lib/projectSync";
import { Workflow } from "@/types/workflow";

export function useWorkflowDAG(projectId?: string) {
  const queryClient = useQueryClient();

  const blocksQuery = useQuery({
    queryKey: queryKeys.workflowBlocks,
    queryFn: () => workflowApi.listBlocks(),
    staleTime: 1000 * 60 * 60,
  });

  const workflowQuery = useQuery({
    queryKey: queryKeys.workflow(projectId),
    queryFn: () => workflowApi.getWorkflow(projectId as string),
    enabled: !!projectId,
  });

  const checklistQuery = useQuery({
    queryKey: queryKeys.workflowChecklist(projectId),
    queryFn: () => workflowApi.checkChecklist(projectId as string),
    enabled: !!projectId,
  });

  /** Audit a candidate flow without saving it — used while editing. */
  const validateChecklistMutation = useMutation({
    mutationFn: ({ workflow, force = false }: { workflow: Workflow; force?: boolean }) => {
      if (!projectId) throw new Error("No project selected");
      return workflowApi.validateChecklist(projectId, workflow, force);
    },
  });

  const saveWorkflowMutation = useMutation({
    mutationFn: ({ workflow, force = false }: { workflow: Workflow; force?: boolean }) => {
      if (!projectId) throw new Error("No project selected");
      return workflowApi.saveWorkflow(projectId, workflow, force);
    },
    onSuccess: (project) => {
      syncProject(queryClient, project);
      void queryClient.invalidateQueries({ queryKey: queryKeys.workflow(projectId) });
      void queryClient.invalidateQueries({
        queryKey: queryKeys.workflowChecklist(projectId),
      });
    },
  });

  const runWorkflowMutation = useMutation({
    mutationFn: (options?: { background?: boolean }) => {
      if (!projectId) throw new Error("No project selected");
      return workflowApi.runWorkflow(projectId, {}, options?.background ?? true);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.workflowRuns(projectId) });
      void queryClient.invalidateQueries({ queryKey: queryKeys.project(projectId) });
      void queryClient.invalidateQueries({ queryKey: queryKeys.projects });
    },
  });

  const runsQuery = useQuery({
    queryKey: queryKeys.workflowRuns(projectId),
    queryFn: () => workflowApi.listRuns(projectId as string),
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