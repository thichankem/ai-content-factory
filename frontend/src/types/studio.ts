/**
 * Studio-only view models.
 *
 * Nothing here travels over HTTP. These are shapes the UI invents for its own
 * screens — timeline lanes, the script brief form, chat messages — and they are
 * kept apart from ``types/`` contract modules so a reader can tell at a glance
 * whether a type describes the API or the interface.
 */

import { VideoScene } from "@/types/timeline";

/** One lane of the multi-track timeline (a UI grouping, not a backend track). */
export interface TimelineTrack {
  id: string;
  name: string;
  type: "video" | "audio" | "voice" | "caption";
  color: string;
  muted?: boolean;
  locked?: boolean;
}

/** A scene placed on a lane at an absolute start time. */
export interface TimelineClip {
  id: string;
  trackId: string;
  sceneIndex: number;
  label: string;
  start: number;
  duration: number;
  color?: string;
  speed?: number;
}

/** Editor tools, mirroring the shortcut set the toolbar exposes. */
export type TimelineTool =
  | "select"
  | "trackSelect"
  | "ripple"
  | "razor"
  | "slip"
  | "pen"
  | "hand"
  | "type";

/** Which monitor panel is showing. */
export type MonitorTab = "program" | "source" | "scopes";

/** The scripting workshop tabs. */
export type ScriptStudioTab = "brief" | "editor" | "chatbot" | "pacing";

/** A flat projection of scenes for lane rendering. */
export interface SceneLane {
  track: TimelineTrack;
  clips: TimelineClip[];
  scene?: VideoScene;
}

/**
 * The scripting brief.
 *
 * Ten sections the operator fills in; the script engine turns them into the
 * prompt. Frontend-only: the backend stores the resulting script, not the brief.
 */
export interface ScriptBriefSettings {
  /** 1. Topic & angle. */
  topic: string;
  uniqueAngle: string;

  /** 2. Platform & format. */
  platform: "tiktok" | "shorts" | "reels" | "youtube_long";
  targetDuration: string;
  aspectRatio: "9:16" | "16:9" | "1:1" | "4:5";
  customDurationSeconds?: number;

  /** 3. Audience. */
  audienceAgeGender: string;
  audienceKnowledge: string;
  audiencePainPoint: string;
  audienceDesire: string;

  /** 4. Video goal. */
  videoGoal: "entertainment" | "education" | "conversion" | "follow" | "viral_debate";
  callToAction: string;

  /** 5. Tone & style. */
  tone: "humorous" | "serious" | "inspiring" | "dramatic" | "casual" | "provocative";
  includeMemeSlang: boolean;
  slangKeywords: string;

  /** 6. Desired structure. */
  hookType:
    | "curiosity_gap"
    | "shocking_stat"
    | "fatal_mistake"
    | "counter_intuitive"
    | "story_teaser";
  structurePacing:
    | "hook_body_climax_cta"
    | "problem_agitate_solution"
    | "myth_busting"
    | "3_step_tutorial";
  includeVisualCues: boolean;

  /** 7. Presentation format. */
  formatType:
    | "talking_head"
    | "voiceover_broll"
    | "two_person_dialogue"
    | "cinematic_storytelling"
    | "pov_demo";

  /** 8. Facts and data, to keep the model from inventing. */
  specificFactsAndData: string;
  referenceLinksAndDocs: string;
  uploadedFiles?: Array<{ name: string; size: number; snippet?: string }>;
  attachedFiles?: Array<{ id: string; name: string; size: number; type: string }>;
  attachedPages?: Array<{ id: string; url: string; note?: string }>;

  /** 9. Reference examples. */
  benchmarkCreatorOrChannel: string;
  benchmarkScriptExample: string;
  benchmarkMediaUrl: string;
  uploadedVideoRef?: { name: string; extractedScript?: string };

  /** 10. Things to avoid. */
  negativeConstraints: string;
  forbiddenWords: string;
}

/** The part of a script a chatbot instruction applies to. */
export interface TargetScope {
  type: "full" | "selection" | "lines" | "section";
  startLine: number;
  endLine: number;
  selectedText: string;
  sectionTitle?: string;
  wordCount: number;
  estimatedSeconds: number;
}

/** Chosen narration pace, used to estimate runtime. */
export interface SpeechPacingConfig {
  wpm: number;
  label: string;
  preset: "slow" | "normal" | "fast" | "hyper" | "custom";
}

/** One turn of the script chatbot. */
export interface ChatbotMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  targetScope?: TargetScope;
  diffBefore?: string;
  diffAfter?: string;
  applied?: boolean;
  canUndo?: boolean;
  timestamp: string;
}

/** Historical snapshot of a script section or full document. */
export interface SectionHistoryEntry {
  id: string;
  sectionKey: string;
  sectionLabel: string;
  version: number;
  text: string;
  summary: string;
  wordCount: number;
  estimatedSeconds: number;
  author: "user" | "ai" | "snapshot";
  timestamp: string;
}