/**
 * Multi-format campaign endpoints.
 *
 * A campaign is generated once per project and then edited short by short, so the
 * generate call is expensive and the update call is cheap.
 */

import * as api from "@/lib/api/client";
import {
  CampaignGenerateRequest,
  MultiFormatCampaign,
  ShortsUpdateRequest,
  ShortsVariant,
} from "@/types/campaign";

/** ``GET /projects/{id}/campaign``. */
export function getCampaign(projectId: string): Promise<MultiFormatCampaign> {
  return api.apiFetch<MultiFormatCampaign>(`/projects/${projectId}/campaign`);
}

/** ``POST /projects/{id}/campaign/generate``. */
export function generateCampaign(
  projectId: string,
  payload: CampaignGenerateRequest = {}
): Promise<MultiFormatCampaign> {
  return api.apiFetch<MultiFormatCampaign>(
    `/projects/${projectId}/campaign/generate`,
    { method: "POST", body: payload }
  );
}

/** ``PUT /projects/{id}/campaign/shorts/{short_id}``. */
export function updateShort(
  projectId: string,
  shortId: string,
  payload: ShortsUpdateRequest
): Promise<ShortsVariant> {
  return api.apiFetch<ShortsVariant>(
    `/projects/${projectId}/campaign/shorts/${shortId}`,
    { method: "PUT", body: payload }
  );
}

/** ``GET /projects/{id}/campaign/export-pack`` — the publishable bundle. */
export function exportPack(
  projectId: string
): Promise<Record<string, unknown>> {
  return api.apiFetch<Record<string, unknown>>(
    `/projects/${projectId}/campaign/export-pack`
  );
}
