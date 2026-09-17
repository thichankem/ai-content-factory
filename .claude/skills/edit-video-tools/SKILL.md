---
name: edit-video-tools
description: Use when an external AI agent (Claude, Codex, DeepSeek, Gemini) needs to discover and operate the content factory's editing pipeline through the /tools API
---

# Content Factory — Agent Tools

## Discovery

Everything an agent can do is self-described at `GET /tools`. It returns:

- `protocol`: `"content-factory-tools/1"`
- `tools[]`: name, description, informal args schema, category, service method
- `usage_notes`: the canonical pipeline order and conventions

## Calling a tool

```http
POST /tools/call
{"tool": "get_project", "args": {"project_id": "<id>"}}
```

Errors keep domain meaning: 404 not found, 409 state conflict, 403 rights,
422 bad tool/args.

## Canonical pipeline order

1. `create_project` (name, topic, language, duration)
2. `research_project` — web sources + key facts
3. `list_kbs` / `attach_kb` / `ground_project` — bind citations [n]
4. `update_script` — narration with `[Hook]`, `[Turn]`... markers; pass
   `source_rights_confirmed: true` only when a human confirmed rights
5. `analyze_script` — timing + lint before asking for approval
6. `approve_stage` (stage: script) — HUMAN GATE, never auto-confirm
7. `build_video_project` — script becomes an editable timeline
8. Timeline edits: `split_scene`, `merge_scene`, `duplicate_scene`,
   `delete_scene`, `move_scene`, `set_scene_speed`, `reverse_scene`,
   `trim_scene`, `set_scene_audio`, `bulk_update_scenes`, `set_keyframes`,
   `add_marker`, `ai_assist`
9. `timeline_report` (score 0-100) and `render_plan` to verify
10. `generate_voiceover`, `start_generation`
11. `approve_stage` (stage: video) — HUMAN GATE
12. `publish_project`

## Hard rules

- Never set `source_rights_confirmed: true` without an explicit human
  confirmation. Approval gates are always human decisions.
- Scene ids come from `get_project` / `build_video_project` responses.
- Prefer `analyze_script` / `timeline_report` after edits; fix issues
  before requesting the next gate.
