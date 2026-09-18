import { useMutation, useQuery } from "@tanstack/react-query";
import { fetchApi } from "../lib/api-client";

export function useWorkflowCampaign(projectId?: string) {
  const checklistQuery = useQuery({
    queryKey: ["workflow-checklist", projectId],
    queryFn: () => fetchApi<any>(`/projects/${projectId}/workflow/checklist`),
    enabled: !!projectId,
  });

  const runWorkflowMutation = useMutation({
    mutationFn: () =>
      fetchApi<any>(`/projects/${projectId}/workflow/run`, {
        method: "POST",
      }),
  });

  const campaignQuery = useQuery({
    queryKey: ["campaign", projectId],
    queryFn: () => fetchApi<any>(`/projects/${projectId}/campaign`),
    enabled: !!projectId,
  });

  const generateCampaignMutation = useMutation({
    mutationFn: () =>
      fetchApi<any>(`/projects/${projectId}/campaign/generate`, {
        method: "POST",
      }),
  });

  return {
    checklistQuery,
    runWorkflowMutation,
    campaignQuery,
    generateCampaignMutation,
  };
}
