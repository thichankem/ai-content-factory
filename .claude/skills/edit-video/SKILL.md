---
name: edit-video
description: >-
  Open the professional video editor for a project in video review: edit
  scenes on the multitrack timeline (text, duration, speed, transitions,
  filters, Ken Burns, text styles, entrance/exit), export a real WebM, and
  upload it. Use when the user wants to edit/refine the produced video.
---

# Edit and export the video

After production finishes the project reaches `video_review` with an editable
scene-based video project. The browser editor (open via the "Open video
editor" button in the UI) provides:

- Multitrack timeline: Scenes, Text, and Music tracks.
- Per-scene editing: text, duration, speed (0.5x–2x), background color,
  transition (cut / fade / slide / zoom / wipe / circle / dissolve),
  text position and style (title, subtitle, caption, neon, outline, shadow),
  font size, color filter (grayscale, sepia, invert, blur, vignette, warm,
  cool, contrast, brightness), effects (glitch, pixelate, scanlines,
  film-grain, old-film, dreamy, sharpen, mosaic), cinematic color grades
  (teal-orange, noir, vintage, cyberpunk, pastel), keyframe-style motion
  animation (scale, rotation, opacity, offset X/Y, easing), emoji sticker
  overlays (position + size), voice pitch (0.5x–2x), Ken Burns pan/zoom,
  and entrance/exit animations.
- Project settings: aspect ratio (9:16, 16:9, 1:1, 4:5), fps (24/30/60),
  captions, background music (procedural beat at the configured BPM),
  export quality.
- **✨ AI Assist panel**: one-click AI editing —
  - ⚡ **Auto-edit all**: fits durations to text length, suggests the best
    filter/effect/grade/transition per scene, and polishes scene text.
  - 🎵 **Beat sync**: snaps every scene duration to the BPM beat grid.
  - 💡 **Suggest look**: asks the AI for filter/effect/grade/transition for
    the selected scene.
  - ✨ **Polish text**: AI-style rewrite of the selected scene's text.
  - 📝 **Auto-captions**: derives captions from narration and enables them.
- Undo/redo (Ctrl+Z / Ctrl+Shift+Z) and keyboard spacebar play/pause.
- **AI voiceover**: click "🎙 Voiceover" to synthesize narration for every
  scene (Microsoft Edge neural voices via `edge-tts`, `gTTS` fallback). Scene
  durations are automatically re-synced to the narration audio, the voice
  plays back during preview, and it is captured into the exported WebM as an
  Opus audio track alongside the VP9 video. Per-scene pitch is honored.
- **Export**: records the canvas preview into a real WebM and uploads it via
  `POST /projects/{id}/video/upload`; the status line reports the exported
  file size, encode time, and effective fps.

API equivalents:

```bash
# Get the editable video project
curl -s http://127.0.0.1:8080/projects/<PROJECT_ID>/video-project

# Save edits
curl -s -X PUT http://127.0.0.1:8080/projects/<PROJECT_ID>/video-project \
  -H 'Content-Type: application/json' \
  -d '{"project": { ...video project JSON... }}'

# AI auto-edit pipeline (fit durations + beat-sync + looks + polish)
curl -s -X POST http://127.0.0.1:8080/projects/<PROJECT_ID>/video-project/ai-assist \
  -H 'Content-Type: application/json' -d '{"fit": true, "beat": true, "bpm": 120}'

# AI look suggestions for one scene
curl -s http://127.0.0.1:8080/projects/<PROJECT_ID>/video-project/scenes/<SCENE_ID>/suggest

# AI-polish one scene's text
curl -s -X POST http://127.0.0.1:8080/projects/<PROJECT_ID>/video-project/scenes/<SCENE_ID>/polish

# Synthesize narration for every scene (background job; poll the project
# until "voiceover" appears)
curl -s -X POST http://127.0.0.1:8080/projects/<PROJECT_ID>/voiceover/generate

# Fetch the exported video
curl -s http://127.0.0.1:8080/projects/<PROJECT_ID>/video -o video.webm
```

After exporting, the video is attached to the project and ready for the final
human review gate (see the `review-video` skill).