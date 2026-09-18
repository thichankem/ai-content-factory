/**
 * Multi-format campaign hooks.
 *
 * This replaces the old ``useWorkflowCampaign``, which fetched the workflow
 * checklist and the workflow run as well as the campaign — three unrelated
 * concepts behind one `any`-typed hook, duplicated against ``useWorkflowDAG``.
 * Flow runs belong to :func:`@/hooks/useWorkflowDAG.useWorkflowDAG`; this file
 * owns the campaign only.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { campaignApi } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { CampaignGenerateRequest, ShortsUpdateRequest } from "@/types/campaign";

export function useCampaign(projectId?: string) {
  const queryClient = useQueryClient();

  const campaignQuery = useQuery({
    queryKey: queryKeys.campaign(projectId),
    queryFn: () => campaignApi.getCampaign(projectId as string),
    enabled: !!projectId,
  });

  const generateCampaignMutation = useMutation({
    mutationFn: (payload: CampaignGenerateRequest = {}) => {
      if (!projectId) throw new Error("No project selected");
      return campaignApi.generateCampaign(projectId, payload);
    },
    onSuccess: (campaign) => {
      queryClient.setQueryData(queryKeys.campaign(projectId), campaign);
    },
  });

  const updateShortMutation = useMutation({
    mutationFn: ({
      shortId,
      payload,
    }: {
      shortId: string;
      payload: ShortsUpdateRequest;
    }) => {
      if (!projectId) throw new Error("No project selected");
      return campaignApi.updateShort(projectId, shortId, payload);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.campaign(projectId) });
    },
  });

  return {
    campaignQuery,
    generateCampaignMutation,
    updateShortMutation,
  };
}