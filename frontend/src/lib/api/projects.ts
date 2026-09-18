/**
 * Project lifecycle endpoints.
 *
 * Every function here names the route it calls, so the studio's HTTP surface can
 * be reviewed against ``src/content_factory/api/routers/projects.py`` without
 * reading component code.
 */

import * as api from "./client";
import {
  ApprovalCreate,
  Project,
  ProjectCreate,
  PublishCreate,
  ScriptUpdate,
} from "@/types/project";
import { ScriptAnalysis } from "@/types/script";

/** ``GET /projects`` — every project, newest first. */
export function listProjects(): Promise<Project[]> {
  return api.apiFetch<Project[]>("/projects");
}

/** ``GET /projects/{id}``. */
export function getProject(projectId: string): Promise<Project> {
  return api.apiFetch<Project>(`/projects/${projectId}`);
}

/** ``POST /projects``. */
export function createProject(payload: ProjectCreate): Promise<Project> {
  return api.apiFetch<Project>("/projects", { method: "POST", body: payload });
}

/** ``PUT /projects/{id}/script`` — save the raw narration text. */
export function updateScript(
  projectId: string,
  payload: ScriptUpdate
): Promise<Project> {
  return api.apiFetch<Project>(`/projects/${projectId}/script`, {
    method: "PUT",
    body: payload,
  });
}

/** ``POST /projects/{id}/script/generate`` — draft a script with the provider chain. */
export function generateScript(projectId: string): Promise<Project> {
  return api.apiFetch<Project>(`/projects/${projectId}/script/generate`, {
    method: "POST",
  });
}

/** ``PUT /projects/{id}/script/style`` — pick the scripting preset. */
export function selectScriptStyle(projectId: string, style: string): Promise<Project> {
  return api.apiFetch<Project>(`/projects/${projectId}/script/style`, {
    method: "PUT",
    body: { style },
  });
}

/** ``POST /projects/{id}/script/analyze`` — lint and time a candidate script. */
export function analyzeScript(
  projectId: string,
  payload: { script?: string | null; style?: string | null } = {}
): Promise<ScriptAnalysis> {
  return api.apiFetch<ScriptAnalysis>(`/projects/${projectId}/script/analyze`, {
    method: "POST",
    body: payload,
  });
}

/** ``POST /projects/{id}/research`` — run the research engine. */
export function runResearch(projectId: string, web = true): Promise<Project> {
  return api.apiFetch<Project>(`/projects/${projectId}/research`, {
    method: "POST",
    query: { web },
  });
}

/**
 * ``POST /projects/{id}/approvals`` — **Gate 1** (script) or **Gate 2** (video).
 *
 * The state machine rejects an out-of-order decision with HTTP 409; the caller
 * surfaces that message rather than retrying.
 */
export function submitApproval(
  projectId: string,
  payload: ApprovalCreate
): Promise<Project> {
  return api.apiFetch<Project>(`/projects/${projectId}/approvals`, {
    method: "POST",
    body: payload,
  });
}

/** ``POST /projects/{id}/generate`` — start the production worker. */
export function startGeneration(projectId: string): Promise<Project> {
  return api.apiFetch<Project>(`/projects/${projectId}/generate`, {
    method: "POST",
  });
}

/** ``POST /projects/{id}/publish`` — distribute to the approved platforms. */
export function publishProject(
  projectId: string,
  payload: PublishCreate = {}
): Promise<Project> {
  return api.apiFetch<Project>(`/projects/${projectId}/publish`, {
    method: "POST",
    body: payload,
  });
}

/** ``POST /projects/{id}/voiceover/generate`` — synthesise narration for every scene. */
export function generateVoiceover(projectId: string): Promise<Project> {
  return api.apiFetch<Project>(`/projects/${projectId}/voiceover/generate`, {
    method: "POST",
  });
}

/** ``POST /projects/{id}/render`` — render the timeline with ffmpeg. */
export function renderProject(
  projectId: string,
  payload: { export_format?: "webm" | "mp4"; audio_ref?: string | null } = {}
): Promise<Project> {
  return api.apiFetch<Project>(`/projects/${projectId}/render`, {
    method: "POST",
    body: payload,
  });
}

/** ``GET /projects/{id}/video`` — the exported file's URL. */
export function projectVideoUrl(projectId: string, download = false): string {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
  return `${base}/projects/${projectId}/video${download ? "?download=true" : ""}`;
}

/** ``GET /projects/{id}/thumbnail`` — the rendered SVG cover. */
export function projectThumbnailUrl(projectId: string): string {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
  return `${base}/projects/${projectId}/thumbnail`;
}
