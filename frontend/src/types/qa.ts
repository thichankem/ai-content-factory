/**
 * QA, cost, audit and command contract — mirrors ``models/qa.py`` and the
 * response views in ``services/qa.py``.
 *
 * Several of these responses return *two spellings* of the same fact (the
 * canonical engine name and the name the web clients read). Only the second is
 * typed below, because that is what the studio receives; the canonical names
 * stay documented in the backend.
 */

import { IssueSeverity } from "@/types/common";
import { VideoProject } from "@/types/timeline";

/** Payload for ``POST /qa/platform`` and ``/qa/platform/verdict``. */
export interface PlatformCheckRequest {
  platform: string;
  duration_seconds?: number | null;
  aspect_ratio?: string;
  words?: number;
  text?: string;
}

/** Payload for ``POST /qa/brand`` and ``/qa/brand/verdict``. */
export interface BrandCheckRequest {
  dominant_colors?: string[];
  fonts_used?: string[];
  has_logo?: boolean;
  palette?: string[];
  fonts?: string[];
  logo_fingerprints?: string[];
}

/** Payload for ``POST /qa/copyright`` and ``/qa/copyright/verdict``. */
export interface CopyrightCheckRequest {
  fingerprint?: string | null;
  asset_ids?: string[];
  protected?: string[];
}

/** One raw QA finding (the ``/qa/*`` list endpoints return these). */
export interface QaFinding {
  code: string;
  severity: IssueSeverity | "fail" | "pass";
  message: string;
  hint?: string | null;
}

/** ``POST /qa/platform/verdict``. */
export interface PlatformVerdict {
  platform: string;
  passed: boolean;
  issues: string[];
  recommendations: string[];
  findings: QaFinding[];
}

/** ``POST /qa/brand/verdict``. */
export interface BrandVerdict {
  passed: boolean;
  findings: Array<{
    category: string;
    status: "pass" | "warn" | "fail";
    message: string;
    hint?: string | null;
  }>;
}

/** ``POST /qa/copyright/verdict``. */
export interface CopyrightVerdict {
  passed: boolean;
  fingerprints: Array<{ asset_id: string; sha256: string; status: string }>;
  findings: QaFinding[];
  checked: number;
}

/** One immutable audit record (`AuditEntry`). */
export interface AuditEntry {
  ts: string;
  actor: string;
  action: string;
  project_id?: string | null;
  media_id?: string | null;
  prompt?: string | null;
  detail?: string | null;
}

/** Payload for ``POST /audit/record``. */
export interface AuditRecordRequest {
  actor: string;
  action: string;
  project_id?: string | null;
  media_id?: string | null;
  prompt?: string | null;
  detail?: string | null;
}

/** Payload for ``POST /cost/check`` (`CostCheckRequest`). */
export interface CostCheckRequest {
  /** Canonical spelling. */
  calls?: Record<string, number>;
  /** Spelling the studio sends; both are merged by the backend. */
  estimated_usage?: Record<string, number>;
}

/** ``POST /cost/check``. */
export interface CostCheckResult {
  estimate_usd: number;
  breakdown: Record<string, number>;
  needs_confirmation: boolean;
  by_kind: Record<string, number>;
  estimated_total_usd: number;
  exceeds_budget: boolean;
  budget_limit: number;
  estimated_cost: number;
  by_service: Record<string, number>;
  within_budget: boolean;
}

/** Payload for ``POST /script/virality`` (`ViralityRequest`). */
export interface ViralityRequest {
  /** Canonical spelling. */
  script?: string | null;
  /** Spelling the studio sends. */
  script_text?: string | null;
  topic?: string | null;
  duration_seconds?: number | null;
  hook?: string | null;
}

/** ``POST /script/virality``. */
export interface ViralityResult {
  score: number;
  breakdown: Record<string, number>;
  warnings: string[];
  hook_score: number;
  pacing_score: number;
  duration_score: number;
  cta_score: number;
  advice: string[];
  feedback: string[];
  topic: string;
}

/** Payload for ``POST /thumbnail/generate`` and ``/thumbnail/candidates``. */
export interface ThumbnailRequest {
  media_id?: string | null;
  media_path?: string | null;
  project_id?: string | null;
  topic?: string;
  style?: string;
  top_k?: number;
  count?: number | null;
  overlays?: string[];
}

/**
 * One drawn thumbnail candidate (`ThumbnailCandidate`).
 *
 * ``path`` is a **backend filesystem path** — candidates are written to the
 * server's temp directory and there is no route serving them yet, so the studio
 * shows the measurements rather than an image. Serving them is planned;
 * see ``frontend/README.md``.
 */
export interface ThumbnailCandidate {
  path: string;
  timestamp_seconds: number;
  score: number;
  ctr_prediction: number;
}

/** ``POST /thumbnail/candidates`` — the list plus why it may be empty. */
export interface ThumbnailCandidatesResponse {
  candidates: ThumbnailCandidate[];
  count: number;
  empty_reason?: string | null;
  emptyReason?: string | null;
}

/** Payload for ``POST /timeline/command`` (`TimelineCommandRequest`). */
export interface TimelineCommandRequest {
  project: VideoProject;
  /** Canonical spelling. */
  text?: string;
  /** Spelling the command bar sends. */
  command?: string;
}

/** The parse behind a natural-language command. */
export interface ParsedTimelineCommand {
  intent: string;
  target: string;
  target_scene?: string | number | null;
  parameters: Record<string, unknown>;
  description: string;
}

/** ``POST /timeline/command``. */
export interface TimelineCommandResult {
  project: VideoProject;
  command: ParsedTimelineCommand;
  parsed_command: ParsedTimelineCommand;
  message: string;
}

/** Payload for ``POST /subtitles/simplify``. */
export interface SimplifySubtitlesRequest {
  captions: string[];
  level?: string;
}

/** ``POST /subtitles/simplify``. */
export interface SimplifySubtitlesResult {
  level: string;
  captions: Array<{ original: string; simplified: string }>;
}