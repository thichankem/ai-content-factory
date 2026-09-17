---
name: ai-video-editing
description: AI Agent Skill for multi-track NLE video editing: scene breakdown, transition planning, Ken Burns motion, Lumetri color LUT grading, shader effects, and server-authoritative render planning.
allowed-tools:
  - run_command
  - view_file
  - replace_file_content
---

# AI Video Editing Skill — Multi-Track NLE & Render Planning

This skill guides AI agents (OpenAI Codex, Claude, Gemini, DeepSeek) in composing, modifying, and validating non-linear video timelines (`VideoProject`) on the AI Content Factory pipeline.

## 1. Timeline Architecture

A video project consists of sequential `VideoScene` clips on track V1, accompanied by text overlays, background music, voiceover tracks, and timeline markers:

- **Transitions**: `cut` (instant), `fade` (cross-fade), `slide` (push left/right), `zoom` (punch zoom), `wipe` (directional wipe), `circle` (iris dissolve), `dissolve` (additive dissolve).
- **Ken Burns Motion**: `none`, `pan-left`, `pan-right`, `zoom-in`, `zoom-out`.
- **Cinematic Color Grades (LUTs)**:
  - `teal-orange`: Blockbuster Hollywood contrast
  - `noir`: High-contrast black & white cinema
  - `vintage`: Warm 35mm film Kodachrome
  - `cyberpunk`: Vibrant neon cyan & magenta
  - `pastel`: Soft low-contrast aesthetic
- **Shaders & VFX**: `glitch`, `pixelate`, `scanlines`, `film-grain`, `old-film`, `dreamy`, `sharpen`.

## 2. Server-Authoritative Editing Operations

Always perform structural timeline edits through the backend REST endpoints to guarantee state machine validity and maintain revision counters:

- **Split Scene at Playhead**: `POST /projects/{id}/timeline/scenes/{scene_id}/split` with `{"at": 2.5}`
- **Merge with Next Scene**: `POST /projects/{id}/timeline/scenes/{scene_id}/merge`
- **Duplicate Scene**: `POST /projects/{id}/timeline/scenes/{scene_id}/duplicate`
- **Delete Scene**: `DELETE /projects/{id}/timeline/scenes/{scene_id}`
- **Move / Reorder Scene**: `POST /projects/{id}/timeline/scenes/{scene_id}/move` with `{"to_index": 2}`
- **Bulk Update**: `POST /projects/{id}/timeline/scenes/bulk` with `{"scene_ids": [...], "patch": {"filter": "warm"}}`
- **Add Cue Marker**: `POST /projects/{id}/timeline/markers` with `{"time_seconds": 12.0, "label": "Beat drop", "color": "#f59e0b"}`
- **Validate Cut**: `GET /projects/{id}/timeline/report`
- **Compile Render Plan**: `GET /projects/{id}/render-plan`

## 3. TikTok & Vertical Safe Zone Rules

When positioning subtitles and graphics on 9:16 vertical videos:
- Keep vital text between Y: 15% and Y: 75% of canvas height.
- Avoid the right-side rail (X: 82% to 100%) reserved for TikTok's Like, Comment, and Share buttons.
- Avoid the bottom 18% reserved for username, sound marquee, and caption overlay.
