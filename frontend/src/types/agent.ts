/**
 * Agent catalogue and bridge contract — mirrors ``models/agent.py``.
 *
 * The bridge is deliberately narrow: the studio writes a ``brief.md`` for an
 * external agent and reads an ``agent-result.md`` back. Nothing in this module
 * confirms source rights on the operator's behalf.
 */

/** One configured provider in the chain (`AgentInfo`). */
export interface AgentInfo {
  name: string;
  kind: string;
  tier: string;
  enabled: boolean;
  model?: string | null;
  base_url?: string | null;
  breaker: string;
  id: string;
  role: string;
  provider: string;
  capabilities: string[];
}

/** A scripting preset as the catalogue reports it (`CatalogStyle`). */
export interface CatalogStyle {
  id: string;
  name: string;
  description: string;
  tone: string;
}

/** A narration voice as the catalogue reports it (`CatalogVoice`). */
export interface CatalogVoice {
  id: string;
  name: string;
  language: string;
  gender: string;
  engine: string;
  active: boolean;
}

/** Payload for ``GET /agents`` (`AgentCatalog`). */
export interface AgentCatalog {
  strategy: string;
  tts_engine: string;
  agents: AgentInfo[];
  preset_styles: string[];
  script_styles: CatalogStyle[];
  tts_voices: CatalogVoice[];
}

/** Payload for ``POST /projects/{id}/agent-result`` (`AgentResultCreate`). */
export interface AgentResultCreate {
  markdown?: string | null;
  markdown_response?: string | null;
  agent?: string;
}

/** A generated brief handed to an external agent (`AgentBrief`). */
export interface AgentBrief {
  project_id: string;
  agent?: string | null;
  style: string;
  markdown: string;
  generated_at: string;
}

/** Payload for ``POST /tools/call`` (`ToolCallRequest`). */
export interface ToolCallRequest {
  tool: string;
  args?: Record<string, unknown>;
}
