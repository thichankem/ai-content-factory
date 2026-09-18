/**
 * External asset ingestion hooks.
 *
 * Uploads go through the shared API client, which is what makes a multipart
 * request and a JSON request behave the same way on error: both raise
 * :class:`ApiError` carrying the backend's message, instead of the ad-hoc
 * ``fetch``/``res.json()`` error handling this hook used to carry.
 *
 * Ingesting an asset records provenance. It never confirms source rights — only
 * the operator's Gate 1 decision does that.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { externalApi } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import { syncProject } from "@/lib/projectSync";
import {
  ExternalAssetRecord,
  ExternalImportRequest,
} from "@/types/external";

export function useExternalIngestion(projectId?: string) {
  const queryClient = useQueryClient();

  const assetsQuery = useQuery<ExternalAssetRecord[]>({
    queryKey: queryKeys.externalAssets(projectId),
    queryFn: () => externalApi.listAssets(projectId as string),
    enabled: !!projectId,
  });

  const importAssetMutation = useMutation({
    mutationFn: (payload: ExternalImportRequest) => {
      if (!projectId) throw new Error("No project selected");
      return externalApi.importAsset(projectId, payload);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.externalAssets(projectId),
      });
      void queryClient.invalidateQueries({ queryKey: queryKeys.project(projectId) });
    },
  });

  const uploadAssetMutation = useMutation({
    mutationFn: (data: {
      file: File;
      assetType: ExternalImportRequest["asset_type"];
      sceneId?: string;
      attribution?: string;
    }) => {
      if (!projectId) throw new Error("No project selected");
      return externalApi.uploadAsset(projectId, data);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.externalAssets(projectId),
      });
      void queryClient.invalidateQueries({ queryKey: queryKeys.project(projectId) });
    },
  });

  const batchImportMutation = useMutation({
    mutationFn: (items: ExternalImportRequest[]) => {
      if (!projectId) throw new Error("No project selected");
      return externalApi.batchImport(projectId, { items });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.externalAssets(projectId),
      });
    },
  });

  return {
    assetsQuery,
    importAssetMutation,
    uploadAssetMutation,
    batchImportMutation,
  };
}

/** Refresh a project after an ingest that changed its media bindings. */
export function useSyncIngest(projectId?: string) {
  const queryClient = useQueryClient();
  return (project: Parameters<typeof syncProject>[1]) => {
    syncProject(queryClient, project);
    void queryClient.invalidateQueries({
      queryKey: queryKeys.externalAssets(projectId),
    });
  };
}