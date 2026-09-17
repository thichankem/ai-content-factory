---
name: ai-studio-image-voice
description: Use when an AI agent needs to edit photos (Photoshop-style ops/presets), enhance voice audio (Audition-style chain), or duck music under narration via the /studio endpoints and /tools/call
---

# AI Studio — Image & Voice Editing

## Discovery

```http
GET /studio/image/presets   -> presets, ops, filters
GET /studio/voice/presets   -> presets, chain_params, defaults
GET /tools                  -> see tools in category "image" and "voice"
```

## Image editing (Photoshop-style)

Two ways to edit — combine freely:

1. **Named preset** (one-click look): `thumbnail`, `cinematic`, `noir`,
   `clean`, `square` (1080×1080), `vertical` (1080×1920).
2. **Ops pipeline** — applied in order, later ops compose on earlier ones:

| Op | Key params |
|---|---|
| `resize` | width, height, fit |
| `crop` | left, top, width, height |
| `rotate` / `flip` | degrees / horizontal |
| `tone` | brightness, contrast, saturation (1.0 = unchanged) |
| `curves` | shadows, mids, highlights (-1..1) |
| `color_balance` | red, green, blue (-1..1) |
| `filter` | preset: grayscale sepia noir vintage cool warm vivid fade |
| `vignette` | strength (0..1) |
| `blur` / `sharpen` | radius / percent |
| `text` | text, size, color, position, stroke_width |
| `padding` | width, height, color (letterbox to canvas) |
| `auto_enhance` | — (histogram stretch + color + sharpen) |
| `remove_background` | color (hex or `auto`), tolerance (0..1) |

Tool call: `POST /tools/call`
```json
{"tool": "edit_image", "args": {"image_b64": "<base64>",
 "ops": [{"name": "filter", "params": {"preset": "vivid"}},
         {"name": "text", "params": {"text": "TOP 5", "size": 90}}],
 "format": "png"}}
```
Response contains `url` (`/edited/<file>`) — download it there.

## Voice enhancement (Audition-style)

Chain order: highpass → noise gate → de-ess → 3-band EQ → (telephone) →
compressor → reverb → loudness (LUFS target) → fades.

- Presets: `podcast` (-16 LUFS), `voiceover` (-14), `soft`, `telephone`, `raw`.
- Tunable params: `highpass_hz`, `gate_db` (null = off), `de_ess` (0..1),
  `eq_low/eq_mid/eq_high`, `compressor_ratio`, `compressor_threshold_db`,
  `target_lufs`, `reverb_mix`, `telephone`, `fade_in`, `fade_out`.

Tool call: `{"tool": "enhance_voice", "args": {"audio_b64": "...",
"preset": "voiceover"}}`.

**Ducking**: `{"tool": "duck_music", "args": {"voice_b64": "...",
"music_b64": "...", "duck_db": -12}}` — music automatically lowers wherever
the voice is loud. Use for background beds under narration.

## Rules of thumb

- Voice for video: `voiceover` preset; for podcast: `podcast`.
- Thumbnails: `thumbnail` preset + `text` op with a big size (80–140).
- Vertical shorts: end image pipelines with `padding` 1080×1920.
- Every result is persisted server-side and returned as `url` + metadata;
  report fields (steps_applied, peaks, LUFS) are for verification.
