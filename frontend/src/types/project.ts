/**
 * The project lifecycle contract.
 *
 * Mirrors ``src/content_factory/models/project.py``. Three facts the studio is
 * written against, each of which a hand-written guess got wrong before:
 *
 * * ``Project.script`` is the **raw narration text** (a string) — it is what the
 *   renderer narrates and the linter analyses. The bundle an editor binds to
 *   (topic, style, parsed sections, timing plan) is ``Project.script_document``.
 * * ``Project.video`` is a :interface:`VideoAsset`, not a URL string.
 * * the publish payload is ``{platforms: [...]}``, not ``{destinations: [...]}``.
 *
 * Types that belong to another domain module are *not* duplicated here: scenes
 * live in ``./timeline``, the script bundle in ``./script``, research in
 * ``./research``. That keeps each concept in exactly one place and keeps the
 * barrel in ``./index`` free of colliding export names.
 */

import { ApprovalRecord, ProjectStatus } from "./common";
import { ScriptAnalysis, ScriptDocument, ScriptPlan, ScriptIssue } from "./script";
import { ResearchBundle } from "./research";
import { VideoProject } from "./timeline";
import { VoiceoverBundle } from "./voice";
import { Workflow } from "./workflow";
import { MultiFormatCampaign } from "./campaign";
import { ExternalAssetRecord } from "./external";
import {
  FactReconciliationReport,
  SensitivityAuditReport,
  StructuredTimeline,
} from "./history";

/** Payload for ``POST /projects`` (`ProjectCreate`). */
export interface ProjectCreate {
  name: string;
  topic: string;
  target_language?: string;
  duration_target_seconds?: number;
}

/**
 * Payload for ``PUT /projects/{id}/script`` (`ScriptUpdate`).
 *
 * ``script`` is the canonical field and ``raw_script`` is the alias the studio
 * sends; the backend accepts either, and the model keeps them in sync.
 */
export interface ScriptUpdate {
  script?: string | null;
  raw_script?: string | null;
  source_rights_confirmed?: boolean;
}

/** Payload for ``POST /projects/{id}/approvals`` (`ApprovalCreate`). */
export interface ApprovalCreate {
  stage: "script" | "video";
  verdict: "approved" | "rejected";
  comment?: string | null;
}

/** Payload for ``POST /projects/{id}/publish`` (`PublishCreate`). */
export interface PublishCreate {
  /** Destinations to publish to. Omitted means the default (``youtube``). */
  platforms?: string[];
}

/** The produced video asset (`VideoAsset`). */
export interface VideoAsset {
  asset_url: string;
  thumbnail_url: string;
  duration_seconds: number;
  format: string;
  size_bytes?: number | null;
}

/** A document attached to a project (`DocumentRef`). */
export interface DocumentRef {
  id: string;
  title: string;
  source: string;
  doi?: string | null;
  url?: string | null;
  pdf_path?: string | null;
  added_at: string;
}

/**
 * A project (`Project`).
 *
 * Every field the backend serialises is listed; a given screen reads a subset.
 * Fields that are nullable or defaulted on the backend stay optional here, so no
 * screen assumes a value the API did not send.
 */
export interface Project {
  id: string;
  name: string;
  topic: string;
  target_language: string;
  duration_target_seconds: number;
  status: ProjectStatus;
  /** Raw narration text — not the structured bundle. */
  script?: string | null;
  /** The structured view of ``script``, for editors. */
  script_document?: ScriptDocument | null;
  source_rights_confirmed: boolean;
  approvals: ApprovalRecord[];
  provider_used?: string | null;
  error?: string | null;
  progress?: number | null;
  video?: VideoAsset | null;
  platforms: string[];
  published_at?: string | null;
  research?: ResearchBundle | null;
  documents: DocumentRef[];
  knowledge_base_id?: string | null;
  video_project?: VideoProject | null;
  voiceover?: VoiceoverBundle | null;
  script_style: string;
  script_plan?: ScriptPlan | null;
  script_issues: ScriptIssue[];
  analysis?: ScriptAnalysis | null;
  agent_used?: string | null;
  workflow?: Workflow | null;
  campaign?: MultiFormatCampaign | null;
  external_assets: ExternalAssetRecord[];
  structured_timeline?: StructuredTimeline | null;
  fact_report?: FactReconciliationReport | null;
  sensitivity_report?: SensitivityAuditReport | null;
  source_media_id?: string | null;
  created_at: string;
  updated_at: string;
}