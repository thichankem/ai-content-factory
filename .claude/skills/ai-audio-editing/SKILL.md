---
name: ai-audio-editing
description: AI Agent Skill for sound design, neural voiceover synthesis (Edge-TTS Vietnamese & English), pitch/speed modulation, sound effects (SFX), BPM tempo grid, and background music ducking.
allowed-tools:
  - run_command
  - view_file
  - replace_file_content
---

# AI Audio Editing Skill — Voiceover, Sound Design & Beat Sync

This skill guides AI agents in synthesizing natural speech, synchronizing scene durations to narration length, placing sound effects, and balancing multi-layer audio.

## 1. Neural Voiceover Synthesis (Edge-TTS)

The factory pipeline features native neural voiceover support with real duration measurement:

- **Vietnamese Neural Voices**:
  - `vi-VN-HoaiMyNeural` (Female): Warm, clear, expressive narration ideal for educational & story content.
  - `vi-VN-NamMinhNeural` (Male): Authoritative, energetic, punchy tone for tech, news, and viral hooks.
- **English Neural Voices**:
  - `en-US-JennyNeural` (Female), `en-US-GuyNeural` (Male), `en-US-ChristopherNeural` (Male).

### Synthesis API
- Trigger voiceover generation: `POST /projects/{id}/voiceover/generate`
- Retrieve audio stream for scene: `GET /projects/{id}/voiceover/{scene_id}`
- Set volume & pitch: `pitch` range [0.5, 2.0], `voiceover_volume` range [0.0, 1.0].

## 2. BPM Beat Sync & Rhythm Editing

- Short-form vertical videos thrive on rhythmic cuts.
- **Target BPM**: 110 to 130 BPM for energetic pacing.
- **Beat Alignment**: Use `POST /projects/{id}/video-project/ai-assist` with `{"beat": true, "bpm": 120}` to snap clip cut points to musical quarter notes (e.g. 0.5s intervals at 120 BPM).

## 3. Sound Effects (SFX) Design

Complement visual scene transitions and hook moments with synchronized sound effects:
- `whoosh`: Fast directional air sweep for dynamic slide / whip zoom transitions.
- `pop`: Crisp bubble pop for caption chips or sticker popups.
- `camera`: Dual micro-click shutter sound for key fact reveals or photo captures.
- `impact`: Low sub-bass boom (32-80 Hz) for dramatic twists and `[Turn]` sections.
- `level`: Ascending chime arpeggio for `[Payoff]` insights.
- `ding`: Crystal bell notification for CTA triggers.

## 4. Audio Ducking Rule

When voiceover narration is active:
- Background music volume automatically ducks to 15-20% (`music_volume = 0.18`).
- Between narration gaps, music swells back to 35-45% for energy retention.
