/** Narration voiceover contract — mirrors ``models/voice.py``. */

/** One generated narration clip for a scene. */
export interface VoiceoverTrack {
  scene_id: string;
  audio_url: string;
  duration_seconds: number;
  text: string;
}

/** Every narration clip of a project plus how they were produced. */
export interface VoiceoverBundle {
  tracks: VoiceoverTrack[];
  engine: string;
  voice: string;
  generated_at: string;
}
