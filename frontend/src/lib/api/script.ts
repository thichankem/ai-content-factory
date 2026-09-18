/**
 * Scripting preset and virality endpoints.
 *
 * Presets are the operator's tuning surface: they live as JSON/Markdown files on
 * the server and drive the prompt the script engine builds.
 */

import * as api from "./client";
import { ScriptStyle } from "@/types/script";
import { ViralityRequest, ViralityResult } from "@/types/qa";

/** ``GET /script/styles`` — every preset the studio can offer. */
export function listStyles(): Promise<ScriptStyle[]> {
  return api.apiFetch<ScriptStyle[]>("/script/styles");
}

/** ``GET /script/styles/{name}``. */
export function getStyle(name: string): Promise<ScriptStyle> {
  return api.apiFetch<ScriptStyle>(
    `/script/styles/${encodeURIComponent(name)}`
  );
}

/** ``GET /script/styles/{name}/md`` — the preset as Markdown. */
export function getStyleMarkdown(name: string): Promise<string> {
  return api.apiText(`/script/styles/${encodeURIComponent(name)}/md`);
}

/** ``PUT /script/styles/{name}`` — create or replace a preset. */
export function saveStyle(style: ScriptStyle): Promise<ScriptStyle> {
  return api.apiFetch<ScriptStyle>(
    `/script/styles/${encodeURIComponent(style.name)}`,
    { method: "PUT", body: style }
  );
}

/** ``DELETE /script/styles/{name}``. */
export function deleteStyle(name: string): Promise<Record<string, boolean>> {
  return api.apiFetch<Record<string, boolean>>(
    `/script/styles/${encodeURIComponent(name)}`,
    { method: "DELETE" }
  );
}

/** ``POST /script/virality`` — retention score plus the per-axis breakdown. */
export function scoreVirality(payload: ViralityRequest): Promise<ViralityResult> {
  return api.apiFetch<ViralityResult>("/script/virality", {
    method: "POST",
    body: payload,
  });
}
