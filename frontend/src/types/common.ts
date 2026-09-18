/**
 * Shared value objects: lifecycle enums and the health payload.
 *
 * Mirrors ``src/content_factory/models/common.py``. When the backend adds a
 * status or a severity, add it here in the same commit — the studio renders
 * these strings directly.
 */

/** Lifecycle states of a project (`ProjectStatus`). */
export type ProjectStatus =
  | "draft"
  | "script_review"
  | "script_approved"
  | "generating"
  | "video_review"
  | "video_approved"
  | "published"
  | "failed";

/** The two mandatory human review gates (`ApprovalStage`). */
export type ApprovalStage = "script" | "video";

/** Outcome of a human review gate (`ApprovalVerdict`). */
export type ApprovalVerdict = "approved" | "rejected";

/** How serious a reported finding is (`IssueSeverity`). */
export type IssueSeverity = "info" | "warning" | "error";

/** A single human review decision on a project (`ApprovalRecord`). */
export interface ApprovalRecord {
  stage: ApprovalStage;
  verdict: ApprovalVerdict;
  comment?: string | null;
  created_at: string;
}

/** Payload for ``GET /health`` (`HealthResponse`). */
export interface HealthResponse {
  status: string;
  app: string;
  version: string;
  providers: Record<string, string>;
}

/** A finding reported by the script linter or the timeline validator. */
export interface Issue {
  code: string;
  severity: IssueSeverity;
  message: string;
  hint?: string | null;
}
