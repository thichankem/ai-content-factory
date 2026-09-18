export type ProjectStatus =
  | "draft"
  | "script_review"
  | "script_approved"
  | "generating"
  | "video_review"
  | "video_approved"
  | "published";

export interface ScriptSection {
  name: string;
  text: string;
  duration_target_seconds: number;
  /** The pipeline's own names for the same three values. */
  label?: string;
  unit_count?: number;
  estimated_seconds?: number;
}

export interface TimingPlan {
  total_duration: number;
  estimated_seconds?: number;
  target_seconds?: number;
  fits_target?: boolean;
  sections: Array<{
    name: string;
    text: string;
    words: number;
    estimated_seconds: number;
  }>;
}

/**
 * The structured view of a project's script.
 *
 * The API serves the raw narration text as `Project.script` (a plain string,
 * because that is what the renderer narrates and what the CLI, the agent tools
 * and the legacy dashboard all read) and this bundle as
 * `Project.script_document`. Editors bind to the bundle.
 */
export interface Script {
  topic: string;
  style: string;
  raw_script: string;
  sections: ScriptSection[];
  timing_plan?: TimingPlan;
}

export interface Scene {
  index: number;
  label: string;
  duration: number;
  text?: string;
  asset_url?: string;
  filter?: string;
  effect?: string;
  grade?: string;
  transition?: string;
  volume?: number;
}

export interface VideoProject {
  scenes: Scene[];
  aspect_ratio: string;
  target_duration_seconds: number;
  bgm_asset_url?: string;
  bgm_volume?: number;
}

export interface ResearchSource {
  id: string;
  title: string;
  url: string;
  source_type: string;
  summary: string;
}

export interface ResearchBundle {
  topic: string;
  sources: ResearchSource[];
  key_facts: string[];
}

export interface Project {
  id: string;
  name: string;
  topic: string;
  target_language: string;
  duration_target_seconds: number;
  status: ProjectStatus;
  source_rights_confirmed: boolean;
  /** Raw narration text, as narrated and linted. */
  script?: string;
  /** The structured view of `script`, for editors. */
  script_document?: Script;
  research?: ResearchBundle;
  video_project?: VideoProject;
  created_at: string;
  updated_at: string;
}
