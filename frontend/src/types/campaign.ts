/**
 * Multi-format campaign contract — mirrors ``models/campaign.py``.
 *
 * One root topic becomes one long-form master plus a cluster of standalone
 * vertical shorts, each with its own hook and script.
 */

/** How the media for a campaign is allocated across asset kinds. */
export interface HybridAssetRatio {
  ai_reconstruction: number;
  historical_photo: number;
  dynamic_map: number;
  declassified_doc: number;
  technical_diagram: number;
  kinetic_motion: number;
}

/** One standalone vertical short. */
export interface ShortsVariant {
  id: string;
  title: string;
  angle: string;
  hook: string;
  target_duration_seconds: number;
  script: string;
  hook_type: string;
  scenes: Array<Record<string, unknown>>;
  video_prompts: string[];
  image_prompts: string[];
  voiceover_tone: string;
  call_to_action: string;
}

/** Ready-to-paste prompt packs for external generative tools. */
export interface PromptPack {
  kling_veo_prompts: Array<Record<string, string>>;
  midjourney_prompts: Array<Record<string, string>>;
  suno_prompts: Array<Record<string, string>>;
  elevenlabs_settings: Record<string, unknown>;
}

/** A complete multi-format campaign (`MultiFormatCampaign`). */
export interface MultiFormatCampaign {
  id: string;
  project_id: string;
  master_topic: string;
  youtube_script: string;
  youtube_duration_target_seconds: number;
  youtube_story_structure: Record<string, string>;
  youtube_scenes: Array<Record<string, unknown>>;
  youtube_titles: string[];
  youtube_description: string;
  youtube_chapters: Array<Record<string, string>>;
  tiktok_hooks: string[];
  thumbnail_prompts: string[];
  shorts: ShortsVariant[];
  asset_ratio: HybridAssetRatio;
  prompt_pack: PromptPack;
  fact_check_summary: string;
  created_at: string;
  updated_at: string;
}

/** Payload for ``POST /projects/{id}/campaign/generate``. */
export interface CampaignGenerateRequest {
  shorts_count?: number;
  youtube_target_minutes?: number;
  include_prompts?: boolean;
}

/** Payload for ``PUT /projects/{id}/campaign/shorts/{short_id}``. */
export interface ShortsUpdateRequest {
  title?: string | null;
  script?: string | null;
  hook?: string | null;
  call_to_action?: string | null;
}
