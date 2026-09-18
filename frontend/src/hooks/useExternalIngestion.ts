import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchApi } from "../lib/api-client";

export interface ExternalAssetRecord {
  id: string;
  project_id: string;
  asset_type: "scene_video" | "scene_image" | "narration_audio" | "bgm_audio" | "research_dossier";
  scene_id?: string;
  url?: string;
  local_path?: string;
  attribution?: string;
  metadata?: Record<string, any>;
  created_at: string;
}

export function useExternalIngestion(projectId?: string) {
  const queryClient = useQueryClient();

  const assetsQuery = useQuery({
    queryKey: ["external-assets", projectId],
    queryFn: () => {
      if (!projectId) return [];
      return fetchApi<ExternalAssetRecord[]>(`/projects/${projectId}/external/assets`);
    },
    enabled: !!projectId,
  });

  const importAssetMutation = useMutation({
    mutationFn: (data: {
      asset_type: string;
      url?: string;
      scene_id?: string;
      attribution?: string;
      content_text?: string;
      metadata?: Record<string, any>;
    }) => {
      if (!projectId) throw new Error("No project selected");
      return fetchApi<ExternalAssetRecord>(`/projects/${projectId}/external/import`, {
        method: "POST",
        body: JSON.stringify(data),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["external-assets", projectId] });
      queryClient.invalidateQueries({ queryKey: ["projects", projectId] });
    },
  });

  const uploadAssetMutation = useMutation({
    mutationFn: async (data: {
      file: File;
      asset_type: string;
      scene_id?: string;
      attribution?: string;
    }) => {
      if (!projectId) throw new Error("No project selected");
      const formData = new FormData();
      formData.append("file", data.file);
      formData.append("asset_type", data.asset_type);
      if (data.scene_id) formData.append("scene_id", data.scene_id);
      if (data.attribution) formData.append("attribution", data.attribution);

      const res = await fetch(`/projects/${projectId}/external/upload`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `Upload failed (${res.status})`);
      }
      return res.json() as Promise<ExternalAssetRecord>;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["external-assets", projectId] });
      queryClient.invalidateQueries({ queryKey: ["projects", projectId] });
    },
  });

  const batchImportMutation = useMutation({
    mutationFn: (items: any[]) => {
      if (!projectId) throw new Error("No project selected");
      return fetchApi<ExternalAssetRecord[]>(`/projects/${projectId}/external/batch-import`, {
        method: "POST",
        body: JSON.stringify({ items }),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["external-assets", projectId] });
      queryClient.invalidateQueries({ queryKey: ["projects", projectId] });
    },
  });

  return {
    assetsQuery,
    importAssetMutation,
    uploadAssetMutation,
    batchImportMutation,
  };
}
