/**
 * External asset ingestion contract — mirrors ``models/external.py``.
 *
 * Assets here are produced by *other* tools (AI video/image generators, TTS
 * services, research agents). Ingesting one records where it came from; it never
 * confirms source rights, which stay the operator's call at the review gates.
 */

/** Classification of external AI and third-party media assets. */
export type ExternalAssetType =
  | "scene_video"
  | "scene_image"
  | "voiceover"
  | "background_music"
  | "research_dossier"
  | "fact_check_report"
  | "subtitle";

/** Payload for ``POST /projects/{id}/external/import``. */
export interface ExternalImportRequest {
  asset_type: ExternalAssetType;
  scene_id?: string | null;
  scene_index?: number | null;
  url?: string | null;
  raw_content?: string | null;
  label?: string | null;
  attribution?: string | null;
  metadata?: Record<string, unknown>;
}

/** Payload for ``POST /projects/{id}/external/batch-import``. */
export interface BatchExternalImportRequest {
  items: ExternalImportRequest[];
}

/** A record of an ingested external asset. */
export interface ExternalAssetRecord {
  id: string;
  project_id: string;
  asset_type: ExternalAssetType;
  scene_id?: string | null;
  url?: string | null;
  filename?: string | null;
  label?: string | null;
  attribution?: string | null;
  created_at: string;
}
