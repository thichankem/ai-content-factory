/**
 * Agent catalogue and bridge endpoints.
 *
 * The bridge hands an external agent a Markdown brief and reads its Markdown
 * answer back. On the way back the backend parses the answer and moves the
 * project's state through the same state machine the UI uses — the studio never
 * writes a status itself.
 */

import * as api from "@/lib/api/client";
import { AgentCatalog, AgentResultCreate } from "@/types/agent";
import { Project } from "@/types/project";

/** ``GET /agents`` — the provider chain, presets and voices. */
export function listAgents(): Promise<AgentCatalog> {
  return api.apiFetch<AgentCatalog>("/agents");
}

/** ``GET /projects/{id}/brief.md`` — the brief for one agent, as Markdown. */
export function exportBrief(projectId: string, agent?: string): Promise<string> {
  return api.apiText(`/projects/${projectId}/brief.md`, { query: { agent } });
}

/** ``POST /projects/{id}/agent-result`` — import an agent's Markdown answer. */
export function importAgentResult(
  projectId: string,
  payload: AgentResultCreate
): Promise<Project> {
  return api.apiFetch<Project>(`/projects/${projectId}/agent-result`, {
    method: "POST",
    body: payload,
  });
}
