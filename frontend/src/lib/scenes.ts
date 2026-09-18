/**
 * Building a valid `VideoScene` from the few values a screen actually knows.
 *
 * `VideoScene` mirrors the backend model and carries around thirty fields with
 * defaults (speed, transitions, text styling, keyframes, trim points, audio
 * ramps). Screens that assemble a scene locally — the auto-assemble action, a
 * slide deck, a re-cooked script — only have a label, a duration and some text,
 * and hand-writing the other two dozen fields in every one of them is how those
 * screens drifted out of the contract in the first place.
 *
 * `makeScene` fills the defaults in one place. The backend re-normalises whatever
 * it receives, so these values are a starting point, not an authority.
 */

import {
  ColorGrade,
  EntranceEffect,
  ExitEffect,
  KenBurns,
  OverlayPosition,
  SceneEffect,
  TextPosition,
  TextStyle,
  VideoFilter,
  VideoScene,
  VideoTransition,
} from "@/types/timeline";

/** The values a screen has when it creates a scene by hand. */
export interface SceneSeed {
  /** Position in the timeline. */
  index: number;
  label: string;
  /** Duration in seconds. */
  duration: number;
  text?: string;
  /** A URL for the visual — image or video. */
  assetUrl?: string | null;
  filter?: VideoFilter;
  grade?: ColorGrade;
  transition?: VideoTransition;
  background?: string;
}

/**
 * Create a normalised scene.
 *
 * `duration` is clamped away from zero: a zero-length scene divides badly in the
 * render-plan compiler and in the timeline percentage maths.
 */
export function makeScene(seed: SceneSeed): VideoScene {
  const duration = seed.duration > 0 ? seed.duration : 1;
  return {
    id: `scene-${seed.index}-${Math.random().toString(36).slice(2, 8)}`,
    index: seed.index,
    label: seed.label,
    text: seed.text ?? "",
    narration: null,
    duration_seconds: duration,
    duration,
    speed: 1,
    background: seed.background ?? "#090a0f",
    image_url: seed.assetUrl ?? null,
    video_url: null,
    asset_url: seed.assetUrl ?? null,
    asset_type: null,
    source_attribution: null,
    transition: seed.transition ?? "cut",
    text_position: "center" as TextPosition,
    text_color: "#ffffff",
    font_size: 48,
    text_style: "normal" as TextStyle,
    filter: seed.filter ?? ("none" as VideoFilter),
    ken_burns: "none" as KenBurns,
    entrance: "fade" as EntranceEffect,
    exit: "none" as ExitEffect,
    motion: null,
    effect: "none" as SceneEffect,
    grade: seed.grade ?? ("none" as ColorGrade),
    overlay_emoji: null,
    overlay_pos: "center" as OverlayPosition,
    overlay_size: 48,
    pitch: 1,
    keyframes: [],
    trim_start: 0,
    trim_end: 0,
    reverse: false,
    volume: 1,
    audio_fade_in: 0,
    audio_fade_out: 0,
  };
}

/** Build a whole timeline from seeds, numbering the scenes from zero. */
export function makeScenes(seeds: Omit<SceneSeed, "index">[]): VideoScene[] {
  return seeds.map((seed, index) => makeScene({ ...seed, index }));
}
