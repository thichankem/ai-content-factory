/**
 * Timeline endpoints: the video project, its scenes, markers and renders.
 *
 * Note on ``runTimelineCommand``: the request model lives in the backend's
 * ``models/qa.py`` (it is wired into the QA router), so its types sit in
 * ``@/types/qa`` even though the route is under ``/timeline``.
 */

import * as api from "@/lib/api/client";
import { Project } from "@/types/project";
import { StructuredTimeline } from "@/types/history";
import { TimelineCommandRequest, TimelineCommandResult } from "@/types/qa";
import {
  RenderPlan,
  TimelineMarker,
  TimelineReport,
  VideoProject,
} from "@/types/timeline";

/** ``GET /projects/{id}/video-project`` — the scenes, without the whole project. */
export function getVideoProject(projectId: string): Promise<VideoProject> {
  return api.apiFetch<VideoProject>(`/projects/${projectId}/video-project`);
}

/** ``PUT /projects/{id}/video-project`` — save the whole scene collection. */
export function saveVideoProject(
  projectId: string,
  project: VideoProject
): Promise<Project> {
  return api.apiFetch<Project>(`/projects/${projectId}/video-project`, {
    method: "PUT",
    body: { project },
  });
}

/** ``PUT /projects/{id}/timeline`` — save the timeline (an alias of the above). */
export function saveTimeline(
  projectId: string,
  timeline: VideoProject
): Promise<Project> {
  return api.apiFetch<Project>(`/projects/${projectId}/timeline`, {
    method: "PUT",
    body: timeline,
  });
}

/** ``GET /projects/{id}/timeline/report`` — measurements and validation findings. */
export function getTimelineReport(projectId: string): Promise<TimelineReport> {
  return api.apiFetch<TimelineReport>(`/projects/${projectId}/timeline/report`);
}

/** ``GET /projects/{id}/render-plan`` — the compiled, renderer-ready plan. */
export function getRenderPlan(projectId: string): Promise<RenderPlan> {
  return api.apiFetch<RenderPlan>(`/projects/${projectId}/render-plan`);
}

/** ``POST /projects/{id}/timeline/normalize`` — repair a timeline in place. */
export function normalizeTimeline(projectId: string): Promise<Project> {
  return api.apiFetch<Project>(`/projects/${projectId}/timeline/normalize`, {
    method: "POST",
  });
}

/** ``POST .../scenes/{scene_id}/split`` — razor at a fraction of the scene. */
export function splitScene(
  projectId: string,
  sceneId: string,
  at = 0.5
): Promise<Project> {
  return api.apiFetch<Project>(
    `/projects/${projectId}/timeline/scenes/${sceneId}/split`,
    { method: "POST", body: { at } }
  );
}

/** ``POST .../scenes/{scene_id}/merge`` — fold a scene into the previous one. */
export function mergeScene(projectId: string, sceneId: string): Promise<Project> {
  return api.apiFetch<Project>(
    `/projects/${projectId}/timeline/scenes/${sceneId}/merge`,
    { method: "POST" }
  );
}

/** ``POST .../scenes/{scene_id}/duplicate``. */
export function duplicateScene(
  projectId: string,
  sceneId: string
): Promise<Project> {
  return api.apiFetch<Project>(
    `/projects/${projectId}/timeline/scenes/${sceneId}/duplicate`,
    { method: "POST" }
  );
}

/** ``DELETE .../scenes/{scene_id}``. */
export function deleteScene(projectId: string, sceneId: string): Promise<Project> {
  return api.apiFetch<Project>(
    `/projects/${projectId}/timeline/scenes/${sceneId}`,
    { method: "DELETE" }
  );
}

/** ``POST .../scenes/{scene_id}/move`` — reorder a scene. */
export function moveScene(
  projectId: string,
  sceneId: string,
  toIndex: number
): Promise<Project> {
  return api.apiFetch<Project>(
    `/projects/${projectId}/timeline/scenes/${sceneId}/move`,
    { method: "POST", body: { to_index: toIndex } }
  );
}

/** ``POST .../timeline/scenes/bulk`` — one look applied to many scenes. */
export function bulkUpdateScenes(
  projectId: string,
  sceneIds: string[],
  patch: Record<string, unknown>
): Promise<Project> {
  return api.apiFetch<Project>(`/projects/${projectId}/timeline/scenes/bulk`, {
    method: "POST",
    body: { scene_ids: sceneIds, patch },
  });
}

/** ``POST .../timeline/markers``. */
export function addMarker(
  projectId: string,
  marker: Omit<TimelineMarker, "id">
): Promise<Project> {
  return api.apiFetch<Project>(`/projects/${projectId}/timeline/markers`, {
    method: "POST",
    body: marker,
  });
}

/** ``DELETE .../timeline/markers/{marker_id}``. */
export function removeMarker(
  projectId: string,
  markerId: string
): Promise<Project> {
  return api.apiFetch<Project>(
    `/projects/${projectId}/timeline/markers/${markerId}`,
    { method: "DELETE" }
  );
}

/** ``POST .../scenes/{scene_id}/speed``. */
export function setSceneSpeed(
  projectId: string,
  sceneId: string,
  speed: number
): Promise<Project> {
  return api.apiFetch<Project>(
    `/projects/${projectId}/timeline/scenes/${sceneId}/speed`,
    { method: "POST", body: { speed } }
  );
}

/** ``POST .../scenes/{scene_id}/reverse``. */
export function reverseScene(
  projectId: string,
  sceneId: string,
  reverse = true
): Promise<Project> {
  return api.apiFetch<Project>(
    `/projects/${projectId}/timeline/scenes/${sceneId}/reverse`,
    { method: "POST", body: { reverse } }
  );
}

/** ``POST .../scenes/{scene_id}/trim`` — clip in/out points on the source media. */
export function trimScene(
  projectId: string,
  sceneId: string,
  trim: { trim_start?: number | null; trim_end?: number | null }
): Promise<Project> {
  return api.apiFetch<Project>(
    `/projects/${projectId}/timeline/scenes/${sceneId}/trim`,
    { method: "POST", body: trim }
  );
}

/** ``POST .../scenes/{scene_id}/audio`` — narration gain and ramps. */
export function setSceneAudio(
  projectId: string,
  sceneId: string,
  audio: {
    volume?: number | null;
    fade_in?: number | null;
    fade_out?: number | null;
  }
): Promise<Project> {
  return api.apiFetch<Project>(
    `/projects/${projectId}/timeline/scenes/${sceneId}/audio`,
    { method: "POST", body: audio }
  );
}

/** ``POST .../scenes/{scene_id}/copy`` — snapshot a scene as a clip. */
export function copyScene(
  projectId: string,
  sceneId: string
): Promise<{ clip: Record<string, unknown> }> {
  return api.apiFetch<{ clip: Record<string, unknown> }>(
    `/projects/${projectId}/timeline/scenes/${sceneId}/copy`,
    { method: "POST" }
  );
}

/** ``POST .../timeline/scenes/paste``. */
export function pasteScene(
  projectId: string,
  clip: Record<string, unknown>,
  afterSceneId?: string
): Promise<Project> {
  return api.apiFetch<Project>(`/projects/${projectId}/timeline/scenes/paste`, {
    method: "POST",
    body: { clip, after_scene_id: afterSceneId ?? null },
  });
}

/** ``POST /projects/{id}/video-project/ai-assist`` — fit, beat and re-time. */
export function aiAssist(
  projectId: string,
  payload: { fit?: boolean; beat?: boolean; bpm?: number } = {}
): Promise<Project> {
  return api.apiFetch<Project>(`/projects/${projectId}/video-project/ai-assist`, {
    method: "POST",
    body: payload,
  });
}

/** ``GET .../scenes/{scene_id}/suggest`` — an AI suggestion for one scene. */
export function suggestScene(
  projectId: string,
  sceneId: string
): Promise<Record<string, string>> {
  return api.apiFetch<Record<string, string>>(
    `/projects/${projectId}/video-project/scenes/${sceneId}/suggest`
  );
}

/** ``POST .../scenes/{scene_id}/polish`` — rewrite one scene's text. */
export function polishScene(projectId: string, sceneId: string): Promise<Project> {
  return api.apiFetch<Project>(
    `/projects/${projectId}/video-project/scenes/${sceneId}/polish`,
    { method: "POST" }
  );
}

/** ``POST /projects/{id}/video/upload`` — attach an exported file. */
export function uploadVideo(projectId: string, file: File): Promise<Project> {
  const form = new FormData();
  form.append("file", file);
  return api.apiFetch<Project>(`/projects/${projectId}/video/upload`, {
    method: "POST",
    body: form,
  });
}

/** ``POST /timeline/command`` — apply a natural-language edit instruction. */
export function runTimelineCommand(
  payload: TimelineCommandRequest
): Promise<TimelineCommandResult> {
  return api.apiFetch<TimelineCommandResult>("/timeline/command", {
    method: "POST",
    body: payload,
  });
}

/** ``POST /projects/{id}/timeline/extract`` — the chronological event chain. */
export function extractTimeline(projectId: string): Promise<StructuredTimeline> {
  return api.apiFetch<StructuredTimeline>(
    `/projects/${projectId}/timeline/extract`,
    { method: "POST" }
  );
}

/** ``GET /projects/{id}/voiceover/{scene_id}`` — one narration clip's URL. */
export function voiceoverUrl(projectId: string, sceneId: string): string {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
  return `${base}/projects/${projectId}/voiceover/${sceneId}`;
}