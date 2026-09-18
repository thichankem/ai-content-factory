/**
 * External asset ingestion endpoints.
 *
 * Uploads go through :func:`apiFetch` with a ``FormData`` body, which the client
 * encodes as multipart without a hand-written ``Content-Type`` header.
 */

import * as api from "@/lib/api/client";
import {
  BatchExternalImportRequest,
  ExternalAssetRecord,
  ExternalImportRequest,
} from "@/types/external";

/** ``GET /projects/{id}/external/assets``. */
export function listAssets(projectId: string): Promise<ExternalAssetRecord[]> {
  return api.apiFetch<ExternalAssetRecord[]>(
    `/projects/${projectId}/external/assets`
  );
}

/** ``POST /projects/{id}/external/import`` — register an asset by URL or text. */
export function importAsset(
  projectId: string,
  payload: ExternalImportRequest
): Promise<ExternalAssetRecord> {
  return api.apiFetch<ExternalAssetRecord>(
    `/projects/${projectId}/external/import`,
    { method: "POST", body: payload }
  );
}

/** ``POST /projects/{id}/external/upload`` — register an asset from a file. */
export function uploadAsset(
  projectId: string,
  data: {
    file: File;
    assetType: ExternalImportRequest["asset_type"];
    sceneId?: string;
    attribution?: string;
  }
): Promise<ExternalAssetRecord> {
  const form = new FormData();
  form.append("file", data.file);
  form.append("asset_type", data.assetType);
  if (data.sceneId) form.append("scene_id", data.sceneId);
  if (data.attribution) form.append("attribution", data.attribution);
  return api.apiFetch<ExternalAssetRecord>(
    `/projects/${projectId}/external/upload`,
    { method: "POST", body: form }
  );
}

/** ``POST /projects/{id}/external/batch-import`` — register many assets at once. */
export function batchImport(
  projectId: string,
  payload: BatchExternalImportRequest
): Promise<ExternalAssetRecord[]> {
  return api.apiFetch<ExternalAssetRecord[]>(
    `/projects/${projectId}/external/batch-import`,
    { method: "POST", body: payload }
  );
}