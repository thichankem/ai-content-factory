/**
 * SEO contract — mirrors ``seo/contracts.py`` and the ``services/seo.py`` views.
 *
 * The engine reports a **report**, not a flat score: per-signal status, weighted
 * dimensions, the blockers and a list of measurable quick wins. The studio used
 * to read a made-up ``breakdown``/``fixes`` shape; it now renders the real one.
 */

/** Verdict of one signal. */
export type SeoSignalStatus = "ok" | "warn" | "fail" | "unknown";

/** One scored (or missing) signal of the 70-signal model. */
export interface SeoSignal {
  id: string;
  label: string;
  dimension: string;
  weight: number;
  score?: number | null;
  status: SeoSignalStatus;
  detail: string;
  fix?: string | null;
  blocking: boolean;
}

/** A weighted group of signals. */
export interface SeoDimensionScore {
  key: string;
  label: string;
  weight: number;
  score: number;
  coverage: number;
  signals: SeoSignal[];
}

/** One measured improvement available right now. */
export interface SeoQuickWin {
  signal_id: string;
  label: string;
  points: number;
  fix: string;
}

/** The scored pack, as the backend reports it (`SeoReport`). */
export interface SeoReport {
  platform: string;
  label: string;
  score: number;
  grade: string;
  confidence: number;
  capped: boolean;
  cap_reason?: string | null;
  dimensions: SeoDimensionScore[];
  blocking: SeoSignal[];
  quick_wins: SeoQuickWin[];
  projected_score: number;
  verdict: string;
  metrics: Record<string, number>;
  notes: string[];
}

/** The pack a caller submits for scoring (`SeoPackInput`). */
export interface SeoPackInput {
  title?: string;
  description?: string;
  tags?: string[];
  hashtags?: string[];
  keywords?: string[];
  script?: string;
  hook?: string;
  duration_seconds?: number | null;
  aspect_ratio?: string;
  thumbnail_present?: boolean | null;
  thumbnail_text?: string;
  on_screen_text?: string[];
  has_captions?: boolean | null;
  caption_source?: string;
  has_chapters?: boolean;
  chapter_count?: number;
  has_end_screen?: boolean | null;
  playlist?: string | null;
  sound?: string;
  sound_trending?: boolean | null;
  beat_synced?: boolean | null;
  bpm?: number | null;
  cuts_per_minute?: number | null;
  loop_friendly?: boolean | null;
  intro_seconds?: number | null;
  text_in_safe_zone?: boolean | null;
  publish_hour?: number | null;
  audience_hours?: number[];
  watermark?: boolean | null;
  comment_prompt?: boolean;
  series_part?: number | null;
  duet_stitch_enabled?: boolean | null;
  channel?: string;
  language?: string;
}

/** Payload for ``POST /seo/score`` and ``POST /seo/optimize``. */
export interface SeoScoreRequest {
  platform?: string;
  pack?: SeoPackInput;
}

/** Payload for ``POST /projects/{id}/seo``. */
export interface SeoProjectScoreRequest {
  platform?: string;
  keywords?: string[];
  publish_hour?: number | null;
  audience_hours?: number[];
  description?: string | null;
  tags?: string[];
  hashtags?: string[];
  title?: string | null;
}

/** The optimiser's rewritten pack. */
export interface SeoOptimizedPack {
  title: string;
  description: string;
  hashtags: string[];
  tags: string[];
  hook: string;
  comment_prompt: boolean;
}

/** ``POST /seo/optimize``. */
export interface SeoOptimizeResult {
  platform: string;
  /** Canonical name of the rewritten pack. */
  pack: SeoOptimizedPack;
  /** Alias of ``pack`` for the studio. */
  optimized_pack: SeoOptimizedPack;
  publish_hours: number[];
  /** Canonical list of edits. */
  changes: string[];
  /** Alias of ``changes`` for the studio. */
  applied_fixes: string[];
  gain: number;
  before: SeoReport;
  after: SeoReport;
  projected_score: number;
}

/** Payload for ``POST /seo/ab/plan``. */
export interface SeoAbPlanRequest {
  metric?: string;
  baseline_rate: number;
  relative_lift?: number;
  daily_traffic?: number | null;
  arms?: number;
  alpha?: number;
  power?: number;
}

/** ``POST /seo/ab/plan``. */
export interface SeoAbPlanResult {
  metric: string;
  baseline_rate: number;
  target_rate: number;
  relative_lift: number;
  per_arm: number;
  total: number;
  daily_traffic?: number | null;
  /** ``null`` when no daily traffic was supplied. */
  days?: number | null;
  alpha: number;
  power: number;
  variables_to_hold: string[];
  decision_rule: string;
  read_metric: string;
  // --- the studio's names for the same numbers ----------------------------
  sample_size_per_arm: number;
  total_sample_size: number;
  /** ``0`` means "not estimated", never "instant". */
  estimated_days: number;
  minimum_detectable_effect: number;
}

/** One competitor video supplied to the keyword miner. */
export interface CompetitorVideoInput {
  title: string;
  views?: number;
  channel?: string;
  subscribers?: number;
  days_old?: number | null;
  duration_seconds?: number | null;
}

/** Payload for ``POST /seo/keywords``. */
export interface SeoKeywordRequest {
  keywords: string[];
  competitors?: CompetitorVideoInput[];
  pack?: SeoPackInput | null;
}

/**
 * ``POST /seo/keywords``.
 *
 * The engine returns its own opportunity report; the studio reads the ranked
 * rows only, so the shape stays open beyond the keys it renders.
 */
export interface SeoKeywordResult {
  keywords: Array<{
    keyword: string;
    demand: number;
    competition: number;
    opportunity: number;
    notes?: string[];
  }>;
  [key: string]: unknown;
}