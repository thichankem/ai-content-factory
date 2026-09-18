/**
 * Video timeline contract: scenes, effects, keyframes, markers, render plan.
 *
 * Mirrors ``src/content_factory/models/timeline.py``.
 *
 * ### The two spellings
 *
 * The backend stores ``duration_seconds``/``image_url`` and projects the names
 * the web editor binds to — ``duration``/``asset_url``/``index`` — as **real
 * fields that a client may also send back**, so a round-tripped scene validates.
 * Both spellings are typed here: read whichever the surrounding screen already
 * uses, but prefer the canonical one in new code.
 */

import { IssueSeverity } from "@/types/common";

/** Transition effect between scenes. */
export type VideoTransition =
  | "cut"
  | "fade"
  | "slide"
  | "zoom"
  | "wipe"
  | "circle"
  | "dissolve";

/** Vertical placement of on-screen text. */
export type TextPosition = "top" | "center" | "bottom";

/** One-click colour / treatment filters. */
export type VideoFilter =
  | "none"
  | "grayscale"
  | "sepia"
  | "invert"
  | "blur"
  | "vignette"
  | "warm"
  | "cool"
  | "contrast"
  | "brightness";

/** Pan/zoom motion on a static background. */
export type KenBurns = "none" | "pan-left" | "pan-right" | "zoom-in" | "zoom-out";

/** Text presentation presets. */
export type TextStyle =
  | "normal"
  | "title"
  | "subtitle"
  | "caption"
  | "neon"
  | "outline"
  | "shadow";

/** Entrance animation for a scene's text. */
export type EntranceEffect = "none" | "fade" | "slide-up" | "zoom" | "bounce" | "blur-in";

/** Exit animation for a scene's text. */
export type ExitEffect = "none" | "fade" | "slide-down" | "zoom";

/** Additional visual effect overlays. */
export type SceneEffect =
  | "none"
  | "glitch"
  | "pixelate"
  | "scanlines"
  | "film-grain"
  | "old-film"
  | "dreamy"
  | "sharpen"
  | "mosaic";

/** One-click cinematic colour grades (LUT-style). */
export type ColorGrade =
  | "none"
  | "teal-orange"
  | "noir"
  | "vintage"
  | "cyberpunk"
  | "pastel";

/** Placement of an emoji/sticker overlay. */
export type OverlayPosition =
  | "top-left"
  | "top-right"
  | "center"
  | "bottom-left"
  | "bottom-right";

/** Keyframe-style motion animation for a scene (neutral → target). */
export interface SceneMotion {
  scale: number;
  rotation: number;
  opacity: number;
  pos_x: number;
  pos_y: number;
  easing: string;
}

/** One point on a scene's motion track; ``at`` is a fraction of the duration. */
export interface Keyframe extends SceneMotion {
  at: number;
}

/** A labelled point on the timeline (beat, cue, chapter, note). */
export interface TimelineMarker {
  id: string;
  time_seconds: number;
  label: string;
  color: string;
}

/** A single editable scene in the video project (`VideoScene`). */
export interface VideoScene {
  id: string;
  label: string;
  text: string;
  narration?: string | null;
  /** Canonical duration. */
  duration_seconds: number;
  speed: number;
  background: string;
  /** Canonical visual source. */
  image_url?: string | null;
  video_url?: string | null;
  asset_type?: string | null;
  source_attribution?: string | null;
  transition: VideoTransition;
  text_position: TextPosition;
  text_color: string;
  font_size: number;
  text_style: TextStyle;
  filter: VideoFilter;
  ken_burns: KenBurns;
  entrance: EntranceEffect;
  exit: ExitEffect;
  motion?: SceneMotion | null;
  effect: SceneEffect;
  grade: ColorGrade;
  overlay_emoji?: string | null;
  overlay_pos: OverlayPosition;
  overlay_size: number;
  pitch: number;
  keyframes: Keyframe[];
  trim_start: number;
  trim_end: number;
  reverse: boolean;
  volume: number;
  audio_fade_in: number;
  audio_fade_out: number;
  // --- the editor's names for the same facts (stamped by the backend) ------
  /** Position in ``VideoProject.scenes``. */
  index: number;
  /** Editor alias of ``duration_seconds``. */
  duration?: number | null;
  /** Editor alias of ``image_url`` / ``video_url``. */
  asset_url?: string | null;
}

/** The editable scene-based video project (`VideoProject`). */
export interface VideoProject {
  scenes: VideoScene[];
  aspect_ratio: string;
  fps: number;
  captions: boolean;
  background_music: boolean;
  background_music_url?: string | null;
  music_volume: number;
  voiceover_volume: number;
  export_quality: string;
  bpm: number;
  markers: TimelineMarker[];
  /** Bumped on every saved edit, so a client can detect concurrent edits. */
  revision: number;
  updated_at: string;
  // --- the editor's names for the same facts ------------------------------
  /** Derived: the sum of every scene's duration. */
  target_duration_seconds?: number | null;
  /** Editor alias of ``background_music_url``. */
  bgm_asset_url?: string | null;
  /** Editor alias of ``music_volume``. */
  bgm_volume?: number | null;
}

/** Measured properties of a timeline. */
export interface TimelineStats {
  scene_count: number;
  total_seconds: number;
  narration_seconds: number;
  transition_seconds: number;
  marker_count: number;
  shortest_scene_seconds: number;
  longest_scene_seconds: number;
  average_scene_seconds: number;
  words: number;
  words_per_minute: number;
  cuts_per_minute: number;
}

/** A single finding from the timeline validator. */
export interface TimelineIssue {
  code: string;
  severity: IssueSeverity;
  message: string;
  hint?: string | null;
  scene_id?: string | null;
}

/** Validation + measurement report for a video project. */
export interface TimelineReport {
  stats: TimelineStats;
  issues: TimelineIssue[];
  score: number;
  target_seconds?: number | null;
  generated_at: string;
}
