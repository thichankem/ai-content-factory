/**
 * Universal media library endpoints.
 *
 * ``/media/search`` and ``/media/dedup`` are served by the QA router on the
 * backend but belong to the media library by concept, so they are grouped here.
 */

import * as api from "@/lib/api/client";
import {
  DedupRequest,
  DedupResult,
  MediaIngestUrlRequest,
  MediaItem,
  MediaSearchHit,
  ReCookRequest,
  ReCookResult,
} from "@/types/media";

/** ``GET /media`` — every item in the library. */
export function listMedia(): Promise<MediaItem[]> {
  return api.apiFetch<MediaItem[]>("/media");
}

/** ``GET /media/{id}``. */
export function getMedia(mediaId: string): Promise<MediaItem> {
  return api.apiFetch<MediaItem>(`/media/${mediaId}`);
}

/** ``POST /media/upload`` — multipart upload. */
export function uploadMedia(file: File): Promise<MediaItem> {
  const form = new FormData();
  form.append("file", file);
  return api.apiFetch<MediaItem>("/media/upload", { method: "POST", body: form });
}

/** ``POST /media/from-url`` — download a reference clip into the library. */
export function ingestMediaUrl(payload: MediaIngestUrlRequest): Promise<MediaItem> {
  return api.apiFetch<MediaItem>("/media/from-url", {
    method: "POST",
    body: payload,
  });
}

/** ``DELETE /media/{id}``. */
export function deleteMedia(mediaId: string): Promise<Record<string, boolean>> {
  return api.apiFetch<Record<string, boolean>>(`/media/${mediaId}`, {
    method: "DELETE",
  });
}

/** ``POST /media/{id}/transcribe`` — speech to text with segments. */
export function transcribeMedia(
  mediaId: string,
  language = "en"
): Promise<MediaItem> {
  return api.apiFetch<MediaItem>(`/media/${mediaId}/transcribe`, {
    method: "POST",
    query: { language },
  });
}

/** ``POST /media/{id}/extract-text`` — pull the text out of a document. */
export function extractMediaText(mediaId: string): Promise<MediaItem> {
  return api.apiFetch<MediaItem>(`/media/${mediaId}/extract-text`, {
    method: "POST",
  });
}

/** ``POST /media/{id}/recook`` — re-cut a reference into a new project. */
export function recookMedia(
  mediaId: string,
  payload: ReCookRequest
): Promise<ReCookResult> {
  return api.apiFetch<ReCookResult>(`/media/${mediaId}/recook`, {
    method: "POST",
    body: payload,
  });
}

/** ``POST /media/{id}/convert`` — transcode into another container. */
export function convertMedia(
  mediaId: string,
  targetFormat: string
): Promise<MediaItem> {
  return api.apiFetch<MediaItem>(`/media/${mediaId}/convert`, {
    method: "POST",
    query: { target_format: targetFormat },
  });
}

/** ``GET /media/search`` — ranked matches over transcripts and filenames. */
export function searchMedia(query: string, topK = 10): Promise<MediaSearchHit[]> {
  return api.apiFetch<MediaSearchHit[]>("/media/search", {
    query: { q: query, top_k: topK },
  });
}

/** ``POST /media/dedup`` — an empty ``media_ids`` sweeps the whole library. */
export function findDuplicates(payload: DedupRequest = {}): Promise<DedupResult> {
  return api.apiFetch<DedupResult>("/media/dedup", {
    method: "POST",
    body: payload,
  });
}

/** ``GET /media/{id}/download`` — the raw file's URL. */
export function mediaDownloadUrl(mediaId: string): string {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
  return `${base}/media/${mediaId}/download`;
}