---
name: prompt-master-kling-veo-mj
description: AI Agent Skill for crafting hyper-optimized visual and auditory generation prompts tailored to Kling 1.5, Google Veo 2, Runway Gen-3, Midjourney v6.1, Flux Pro, Suno AI, and ElevenLabs.
allowed-tools:
  - run_command
  - view_file
  - replace_file_content
---

# Prompt Master Skill — Generative Engine Directives (Kling, Veo, Midjourney, Suno, ElevenLabs)

This skill equips AI agents to author production-ready prompt packs for 3rd-party generative media engines.

---

## 1. Kling AI & Google Veo 2 (Cinematic Video Prompts)

### Syntax Blueprint
`[Camera Movement] + [Subject & Action] + [Environment & Weather] + [Lighting & Color Grading] + [Lens & Optical Characteristics] + [Negative Constraints]`

### Best Practices
- **Camera verbs**: Use precise cinematography vocabulary (`Slow forward dolly`, `Isometric top-down crane tilt`, `Violent handheld shake`, `Low-angle tracking shot`).
- **Atmospheric particles**: Always request `volumetric fog`, `dust motes in light beam`, `subtle anamorphic lens flare`, `water spray`.
- **Film texture**: Specify `35mm film grain, shot on Arri Alexa Mini LF, Kodak 5219 color grade`.
- **Aspect ratios**: Explicitly declare `--ar 16:9` for YouTube Master or `--ar 9:16` for TikTok / Shorts.

---

## 2. Midjourney v6.1 & Flux Pro (Image Prompts)

### Syntax Blueprint
`[Style / Medium] + [Core Subject] + [Historical Period Details] + [Lighting / Texture] + [--parameters]`

### Historical & Archival Formula
```text
Authentic 1912 restored archival photograph of [Subject], colorized with historical precision, kodachrome vintage aesthetic, natural overcast daylight, silver halide grain, 8k resolution, documentary photography --ar 16:9 --style raw --v 6.1
```

### High-CTR YouTube Thumbnail Formula
```text
Sensational YouTube thumbnail design for documentary about [Subject]. Split-screen high contrast: Left side pristine magnificent engineering in golden sunlight, Right side dark violent oceanic catastrophe with emergency crimson flare. Bold atmospheric lighting, 8k cinematic render, expressive human face in foreground --ar 16:9 --v 6.1
```

---

## 3. Suno AI v3.5 (Soundtrack & Music Blueprint)

Generate emotion-specific cues with explicit acoustic tags:
- **Opening Tension**: `Dark cinematic orchestral, slow cello melody, ominous sub-bass hum, ticking clock pulse, cinematic horns, crescendo`
- **Catastrophic Climax**: `Epic orchestral, thunderous taiko drums, apocalyptic brass swells, soaring tragic operatic choir, dramatic crescendo`
- **Memorial Resolution**: `Somber solo piano, weeping solitary cello, gentle ocean breeze ambience, reverent quiet memorial tribute`

---

## 4. ElevenLabs Narrator Settings (Documentary Voiceover)

- **Model ID**: `eleven_multilingual_v2`
- **Stability**: `0.65 - 0.70` (High enough for solemn authority, flexible enough for dramatic cadence)
- **Similarity Boost**: `0.85`
- **Style Exaggeration**: `0.35`
- **Recommended Voices**:
  - English: `George (British Documentary Narrator)`, `Marcus (Deep Dramatic)`
  - Vietnamese Fallback: `vi-VN-NamMinhNeural` (Edge-TTS, 0.92 pitch / rate)
