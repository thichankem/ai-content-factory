---
name: edit-video
description: >-
  Edit a produced video: structural edits on the server timeline (split,
  merge, duplicate, delete, reorder, bulk look apply, markers), measure and
  validate the cut, compile a render plan, tweak scenes in the browser
  Studio, synthesize voiceover, and export a real WebM. Use when the user
  wants to edit, refine, clean up, or critique the produced video.
---

# Edit and export the video

After production finishes the project reaches `video_review` with an editable
scene-based video project. See `docs/EDITING.md` for the full model, the
validator rule table, and the render plan contract.

## Server timeline engine (authoritative)

The server owns structure. This is the safest way to clean up a cut, and the
only way an external agent should edit one.

```bash
P=http://127.0.0.1:8080/projects/<PROJECT_ID>

# Measure + validate: score, stats, and findings (contrast, dead air,
# overflow, pacing, transition length, duration drift)
curl -s $P/timeline/report

# Repair the document (ids, ranges, keyframes, opening transition)
curl -s -X POST $P/timeline/normalize

# Structural edits
curl -s -X POST $P/timeline/scenes/<SCENE_ID>/split \
  -H 'Content-Type: application/json' -d '{"at": 0.5}'
curl -s -X POST $P/timeline/scenes/<SCENE_ID>/merge
curl -s -X POST $P/timeline/scenes/<SCENE_ID>/duplicate
curl -s -X DELETE $P/timeline/scenes/<SCENE_ID>
curl -s -X POST $P/timeline/scenes/<SCENE_ID>/move \
  -H 'Content-Type: application/json' -d '{"to_index": 0}'

# Apply one look to many scenes (values are validated, not assigned raw)
curl -s -X POST $P/timeline/scenes/bulk \
  -H 'Content-Type: application/json' \
  -d '{"scene_ids": ["<ID1>", "<ID2>"], "patch": {"grade": "noir", "font_size": 60}}'

# Markers (labelled cues, beats, chapter turns)
curl -s -X POST $P/timeline/markers \
  -H 'Content-Type: application/json' \
  -d '{"time_seconds": 2.5, "label": "beat 1", "color": "#22d3ee"}'
curl -s -X DELETE $P/timeline/markers/<MARKER_ID>

# Compile the render plan: absolute slots, resolved looks, caption cues,
# and the audio layers a renderer consumes
curl -s $P/render-plan
```

A cut stays editable in `generating`, `video_review`, `video_approved`, and
`published` (re-cutting after publish is normal). Every save is normalized and
increments the server-owned `revision`.

## Browser Studio

The Studio ("Open Video Studio") provides:

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
- **Pro Engine bar**: the server engine surfaced in the editor — live score
  and stats, the finding list (click a finding to jump to its scene), and
  buttons for Split, Merge, Duplicate, Delete, reorder, 📍 Marker, 🧹 Clean,
  🩺 Check, and 📋 Render Plan. Each action pushes local tweaks, calls one
  server operation, and adopts the returned document.
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