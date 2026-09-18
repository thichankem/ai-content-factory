/**
 * Script planning, linting and style contract.
 *
 * Mirrors ``src/content_factory/models/script.py``.
 *
 * ``Project.script`` remains the raw text; everything an editor needs *around*
 * that text lives in :interface:`ScriptDocument`, which is what the Script
 * Studio binds to.
 */

import { IssueSeverity } from "./common";

/** One labelled section of a narration script, with timing estimates. */
export interface ScriptSectionInfo {
  index: number;
  label: string;
  text: string;
  unit_count: number;
  estimated_seconds: number;
  share: number;
}

/** A timing plan derived from a script and a target duration (`ScriptPlan`). */
export interface ScriptPlan {
  language: string;
  target_seconds: number;
  estimated_seconds: number;
  fits_target: boolean;
  speech_units_per_second: number;
  sections: ScriptSectionInfo[];
  warnings: string[];
  generated_at: string;
}

/** The structured view of a project's script that editors bind to. */
export interface ScriptDocument {
  topic: string;
  style: string;
  raw_script: string;
  sections: ScriptSectionInfo[];
  timing_plan?: ScriptPlan | null;
  language: string;
  target_seconds: number;
  estimated_seconds: number;
}

/** A single finding from the script linter (`ScriptIssue`). */
export interface ScriptIssue {
  code: string;
  severity: IssueSeverity;
  message: string;
  hint?: string | null;
}

/** The full analysis of a script: timing plan plus quality findings. */
export interface ScriptAnalysis {
  plan: ScriptPlan;
  issues: ScriptIssue[];
  score: number;
}

/** A user-tunable scripting preset (`ScriptStyle`). */
export interface ScriptStyle {
  name: string;
  title: string;
  description: string;
  tone: string;
  structure: string[];
  hook_rules: string[];
  sentence_max_units: number;
  units_per_second: Record<string, number>;
  cta: string;
  banned_phrases: string[];
  language_notes: Record<string, string>;
  max_sections: number;
  builtin: boolean;
}

/** Payload for ``PUT /projects/{id}/script/style``. */
export interface ScriptStyleSelect {
  style: string;
}

/** Payload for ``POST /projects/{id}/script/analyze``. */
export interface ScriptAnalyzeRequest {
  script?: string | null;
  style?: string | null;
}
