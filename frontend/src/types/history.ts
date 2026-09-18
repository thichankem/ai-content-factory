/**
 * Historical research, fact-checking and sensitivity contract.
 *
 * Mirrors the ``history`` models in ``models/history.py``.
 */

/** One dated event inside a structured timeline. */
export interface HistoricalEvent {
  timestamp: string;
  title: string;
  description: string;
  location?: string | null;
  casualties?: number | null;
  source?: string | null;
  is_climax: boolean;
  time_offset_seconds?: number | null;
}

/** A topic broken into a chronological chain of events. */
export interface StructuredTimeline {
  topic: string;
  events: HistoricalEvent[];
  total_span?: string | null;
  climax_event_index?: number | null;
  total_casualties?: number | null;
}

/** How much to trust one claim. */
export type FactConfidence = "verified" | "disputed" | "unverified";

/** One claim extracted from a script, with its sources. */
export interface FactClaim {
  claim_type: string;
  value: string;
  confidence: FactConfidence;
  sources: string[];
  discrepancy_notes: string;
}

/** The fact reconciliation report attached to a project. */
export interface FactReconciliationReport {
  topic: string;
  claims: FactClaim[];
  verified_count: number;
  disputed_count: number;
  overall_confidence: string;
  audit_summary: string;
}

/** Severity of a sensitivity finding. */
export type SensitivitySeverity = "info" | "warning" | "error";

/** One sensitive-content finding. */
export interface SensitivityFinding {
  category: string;
  severity: SensitivitySeverity;
  snippet: string;
  message: string;
  suggestion: string;
}

/** The sensitivity audit report attached to a project. */
export interface SensitivityAuditReport {
  safety_score: number;
  is_safe_for_monetization: boolean;
  findings: SensitivityFinding[];
  disclaimer_required: boolean;
  recommended_disclaimer?: string | null;
}

/** A anniversary event returned by ``GET /history/on-this-day``. */
export interface OnThisDayEvent {
  day: number;
  month: number;
  year: number;
  title: string;
  category: string;
  summary: string;
  casualties_estimate?: string | null;
  suggested_angle: string;
  keywords: string[];
}