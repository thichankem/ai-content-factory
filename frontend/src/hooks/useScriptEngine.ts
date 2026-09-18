import { useMutation, useQuery } from "@tanstack/react-query";
import { fetchApi } from "../lib/api-client";
import { ViralityScoreResult } from "../types/api";
import { Project } from "../types/project";

export function useScriptEngine(projectId?: string) {
  const viralityMutation = useMutation({
    mutationFn: ({ scriptText, topic }: { scriptText: string; topic: string }) =>
      fetchApi<ViralityScoreResult>("/script/virality", {
        method: "POST",
        body: JSON.stringify({ script_text: scriptText, topic }),
      }),
  });

  const analyzeScriptMutation = useMutation({
    mutationFn: (data?: { script_text?: string; style?: string }) =>
      fetchApi<any>(`/projects/${projectId}/script/analyze`, {
        method: "POST",
        body: data ? JSON.stringify(data) : undefined,
      }),
  });

  const updateScriptMutation = useMutation({
    mutationFn: (payload: { raw_script: string; source_rights_confirmed?: boolean }) =>
      fetchApi<Project>(`/projects/${projectId}/script`, {
        method: "PUT",
        body: JSON.stringify(payload),
      }),
  });

  const stylesQuery = useQuery({
    queryKey: ["script-styles"],
    queryFn: () => fetchApi<Array<{ name: string; title: string; tone: string }>>("/script/styles"),
  });

  return {
    viralityMutation,
    analyzeScriptMutation,
    updateScriptMutation,
    stylesQuery,
  };
}
