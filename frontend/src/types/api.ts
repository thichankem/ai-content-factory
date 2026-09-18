import { Project, VideoProject } from "./project";

export interface ViralityScoreResult {
  score: number;
  hook_score: number;
  pacing_score: number;
  duration_score: number;
  cta_score: number;
  advice: string[];
}

export interface PlatformQAResult {
  platform: string;
  passed: boolean;
  issues: string[];
  recommendations: string[];
}

export interface BrandKitQAResult {
  passed: boolean;
  findings: Array<{
    category: string;
    status: "pass" | "warn" | "fail";
    message: string;
  }>;
}

export interface CopyrightCheckResult {
  passed: boolean;
  fingerprints: Array<{
    asset_id: string;
    sha256: string;
    status: string;
  }>;
}

export interface ThumbnailCandidate {
  id: string;
  timestamp: number;
  data_url: string;
  predicted_ctr: number;
  style: string;
}

export interface CostCheckResult {
  within_budget: boolean;
  estimated_cost: number;
  budget_limit: number;
  by_service: Record<string, number>;
}

export interface AuditRecord {
  id: string;
  timestamp: string;
  actor: string;
  action: string;
  project_id?: string;
  sha256_hash: string;
}

export interface NLCommandResult {
  parsed_command: {
    intent: string;
    target_scene?: number;
    parameters: Record<string, any>;
  };
  project: VideoProject;
  message: string;
}
