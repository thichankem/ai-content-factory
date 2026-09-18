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
}

export interface TimingPlan {
  total_duration: number;
  sections: Array<{
    name: string;
    text: string;
    words: number;
    estimated_seconds: number;
  }>;
}

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
  script?: Script;
  research?: ResearchBundle;
  video_project?: VideoProject;
  created_at: string;
  updated_at: string;
}
