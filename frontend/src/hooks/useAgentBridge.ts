/**
 * Universal Agent Bridge hooks.
 *
 * The bridge is two calls in opposite directions: export the project's
 * ``brief.md`` for an agent to read, and import the ``agent-result.md`` it wrote
 * back. The import is what moves the project through the state machine — the
 * studio never sets a status itself.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { agentsApi } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { syncProject } from "@/lib/projectSync";

export function useAgentBridge(projectId?: string) {
  const queryClient = useQueryClient();

  const catalogQuery = useQuery({
    queryKey: queryKeys.agentCatalog,
    queryFn: () => agentsApi.listAgents(),
    staleTime: 1000 * 60 * 10,
  });

  /** The brief, as Markdown. Empty when no project is selected. */
  const getBrief = (agentName?: string): Promise<string> => {
    if (!projectId) return Promise.resolve("");
    return agentsApi.exportBrief(projectId, agentName);
  };

  const importResultMutation = useMutation({
    mutationFn: (payload: { markdown_response: string; agent?: string }) => {
      if (!projectId) throw new Error("No project selected");
      return agentsApi.importAgentResult(projectId, payload);
    },
    onSuccess: (project) => syncProject(queryClient, project),
  });

  return {
    catalogQuery,
    getBrief,
    importResultMutation,
  };
}