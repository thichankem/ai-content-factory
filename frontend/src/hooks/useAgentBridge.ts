import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchApi } from "../lib/api-client";
import { Project } from "../types/project";

export interface AgentInfo {
  id: string;
  name: string;
  role: string;
  provider: string;
  enabled: boolean;
  model: string;
  capabilities: string[];
}

export interface AgentCatalogResponse {
  agents: AgentInfo[];
  script_styles: Array<{ id: string; name: string; description: string }>;
  tts_voices: Array<{ id: string; name: string; language: string; gender: string }>;
}

export function useAgentBridge(projectId?: string) {
  const queryClient = useQueryClient();

  const catalogQuery = useQuery({
    queryKey: ["agent-catalog"],
    queryFn: () => fetchApi<AgentCatalogResponse>("/agents"),
    staleTime: 1000 * 60 * 10, // 10 mins
  });

  const getBrief = async (agentName?: string): Promise<string> => {
    if (!projectId) return "";
    const url = `/projects/${projectId}/brief.md${agentName ? `?agent=${encodeURIComponent(agentName)}` : ""}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Failed to load brief.md (${res.status})`);
    return res.text();
  };

  const importResultMutation = useMutation({
    mutationFn: (data: { markdown_response: string; agent?: string }) => {
      if (!projectId) throw new Error("No project selected");
      return fetchApi<Project>(`/projects/${projectId}/agent-result`, {
        method: "POST",
        body: JSON.stringify(data),
      });
    },
    onSuccess: (updated) => {
      queryClient.setQueryData(["projects", projectId], updated);
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });

  return {
    catalogQuery,
    getBrief,
    importResultMutation,
  };
}
