/**
 * Building scenes and video projects on the client.
 *
 * The backend serialises *every* field of a :interface:`VideoScene`, and it
 * validates the ones it receives, so a scene the studio invents for itself has to
 * carry the full set — the screens used to build a four-key object
 * (``index``/``label``/``duration``/``text``) and the save was rejected. The
 * factories here hold the defaults in one place, so a screen describes only the
 * parts it actually decides and every locally-built scene round-trips.
 *
 * The defaults mirror ``models/timeline.py``: ``score``-bearing fields stay inside
 * their documented ranges (``font_size``/``pitch``/``volume``), and the editor's
 * names (``duration``, ``asset_url``) are stamped beside the canonical ones the
 * way the backend's ``_sync_editor_names`` validator does.
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
  VideoProject,
  VideoScene,
  VideoTransition,
} from "@/types/timeline";

/** What a caller may decide about a new scene; everything else is defaulted. */
export interface SceneDraft {
  id?: string;
  label?: string;
  text?: string;
  /** Duration in seconds; ``duration`` is the editor's name for it. */
  duration?: number;
  filter?: VideoFilter;
  grade?: ColorGrade;
  transition?: VideoTransition;
  effect?: SceneEffect;
  background?: string;
  image_url?: string | null;
  video_url?: string | null;
  narration?: string | null;
}

/**
 * Build a complete :interface:`VideoScene` at ``index``.
 *
 * ``index`` is passed in rather than defaulted because only the caller knows the
 * position; the backend re-stamps it on save, but the local timeline renders it
 * before that happens.
 */
export function createScene(index: number, draft: SceneDraft = {}): VideoScene {
  const duration = draft.duration ?? 5;
  return {
    id: draft.id ?? `scene-${index + 1}-${Date.now()}`,
    index,
    label: draft.label ?? `Scene ${index + 1}`,
    text: draft.text ?? "",
    narration: draft.narration ?? null,
    duration_seconds: duration,
    duration,
    speed: 1,
    background: draft.background ?? "#000000",
    image_url: draft.image_url ?? null,
    video_url: draft.video_url ?? null,
    asset_url: draft.image_url ?? draft.video_url ?? null,
    asset_type: draft.video_url ? "video" : draft.image_url ? "image" : null,
    source_attribution: null,
    transition: draft.transition ?? "fade",
    text_position: "center" satisfies TextPosition,
    text_color: "#ffffff",
    font_size: 48,
    text_style: "normal" satisfies TextStyle,
    filter: draft.filter ?? "none",
    ken_burns: "none" satisfies KenBurns,
    entrance: "fade" satisfies EntranceEffect,
    exit: "none" satisfies ExitEffect,
    motion: null,
    effect: draft.effect ?? "none",
    grade: draft.grade ?? "none",
    overlay_emoji: null,
    overlay_pos: "top-right" satisfies OverlayPosition,
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

/** Build a complete :interface:`VideoProject` around a list of scenes. */
export function createVideoProject(
  scenes: VideoScene[],
  overrides: Partial<VideoProject> = {}
): VideoProject {
  const musicVolume = overrides.music_volume ?? 0;
  return {
    scenes,
    aspect_ratio: overrides.aspect_ratio ?? "9:16",
    fps: overrides.fps ?? 30,
    captions: overrides.captions ?? true,
    background_music: overrides.background_music ?? false,
    background_music_url: overrides.background_music_url ?? null,
    music_volume: musicVolume,
    bgm_volume: overrides.bgm_volume ?? musicVolume,
    voiceover_volume: overrides.voiceover_volume ?? 1,
    export_quality: overrides.export_quality ?? "high",
    bpm: overrides.bpm ?? 120,
    markers: overrides.markers ?? [],
    revision: overrides.revision ?? 1,
    updated_at: overrides.updated_at ?? new Date().toISOString(),
    target_duration_seconds:
      overrides.target_duration_seconds ??
      Math.round(scenes.reduce((total, scene) => total + scene.duration_seconds, 0) * 100) / 100,
  };
}