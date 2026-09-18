---
name: universal-agent-bridge
description: >-
  Universal Tool & Integration Protocol for ALL AI Agents (Antigravity, Claude Code,
  Cursor, Codex, DeepSeek, Gemini CLI). Documents the 61-tool REST registry (/tools/call),
  the Model Context Protocol (MCP) server, and the plain-Markdown file bridge (brief.md).
allowed-tools:
  - Read
  - Write
  - Bash
---

# Universal AI Agent Bridge & Tool Registry

The **AI Content Factory** provides three distinct, first-class ways for **any external AI agent** (Google Antigravity, Claude Code, Cursor, Codex CLI, DeepSeek, Gemini CLI, or custom autonomous scripts) to inspect, direct, and edit video pipelines:

```
                      ┌───────────────────────────────────────────┐
                      │             AI Content Factory            │
                      └─────┬───────────────────┬───────────┬─────┘
                            │                   │           │
                     Protocol 1:         Protocol 2:   Protocol 3:
                     Tool API (/tools)    MCP Server    Markdown Bridge
                            │                   │           │
     ┌──────────────────────┴───────┐           │           │
     │ - 61 Tools with JSON Schema  │           │           │
     │ - Chainable by asset_id      │           │           │
     │ - Strict error mapping       │           │           │
     └──────────────────────────────┘           │           │
                            ┌───────────────────┴───┐       │
                            │ - stdio / SSE (8765)  │       │
                            │ - Sandboxed media ops │       │
                            │ - Real-time tool-call │       │
                            └───────────────────────┘       │
                                        ┌───────────────────┴───────┐
                                        │ - brief.md export         │
                                        │ - Plain text / JSON fence │
                                        │ - Offline / copy-paste    │
                                        └───────────────────────────┘
```

---

## 🛠️ Protocol 1: The 61-Tool Registry (`/tools` and `/tools/call`)

Any agent capable of making HTTP requests can operate the entire factory through two endpoints:
- `GET /tools`: Retrieves the self-describing manifest containing all 61 tools with real JSON Schemas (`input_schema`).
- `POST /tools/call`: Executes a tool with payload `{"tool": "<name>", "args": { ... }}`.

### 9 Tool Groups

1. **`discovery`**: `list_projects`, `get_project`, `inspect_media`, `system_health`.
2. **`research`**: `research_project`, `attach_kb`, `ground_project`.
3. **`script`**: `update_script`, `analyze_script`, `rewrite_script`, `suggest_hooks`.
4. **`timeline`**: `build_video_project`, `split_scene`, `merge_scene`, `duplicate_scene`, `delete_scene`, `move_scene`, `set_scene_speed`, `reverse_scene`, `trim_scene`, `set_scene_audio`, `bulk_update_scenes`, `set_keyframes`, `add_marker`, `ai_assist`, `timeline_report`, `render_plan`.
5. **`media`** (Non-Vision Media Perception): `describe_media`, `media_loudness`, `media_silence`, `media_scene_cuts`, `media_palette`, `media_contact_sheet`, `cut_media`, `split_media`, `join_media`, `extract_audio_track`, `extract_frame_image`.
6. **`audio`**: `music_beat_grid`, `audio_trim`, `audio_fade`, `audio_loop`, `audio_normalize`, `audio_retime`, `audio_mix`.
7. **`image`**: `compose_images`, `collage_images`, `image_crop`, `image_remove_background`, `image_upscale`.
8. **`voice`**: `voice_synthesize_speech`, `audio_diarize_speakers`, `audio_detect_speech_emotion`.
9. **`production`**: `approve_stage`, `start_generation`, `publish_project`.

---

## ⚡ Protocol 2: Model Context Protocol (MCP)

For agents natively supporting MCP (Cursor, Claude Desktop, Antigravity, Windsurf, Roo Code):

### Running the MCP Server
```bash
# Stdio mode (for CLI agents and IDEs)
python mcp_server.py

# SSE mode (for networked agents)
python mcp_server.py --sse
```

---

## 📝 Protocol 3: The Markdown File Bridge (`brief.md`)

When working completely offline or via chat-based LLMs without network tool access:

1. **Export Brief**: `GET /projects/{id}/brief.md > brief.md`.
2. **Hand to Agent**: Agent reads `brief.md` containing topic, style rules, timeline, and current script.
3. **Agent Responds**: Agent outputs structured Markdown blocks (`script`, `json scenes`, `json style`).
4. **Ingest Result**: `POST /projects/{id}/agent-result` with payload `{"markdown": "...", "agent": "<name>"}`.

---

## ⚖️ Immutable Safety Rules for All AI Agents

1. **Source Rights Are Sacred**: No agent is ever permitted to set `source_rights_confirmed: true` autonomously. A human operator must verify licensing.
2. **Two Human Review Gates**:
   - **Gate 1 (`script_review`)**: Requires human approval before video production starts.
   - **Gate 2 (`video_review`)**: Requires human approval before publishing.
3. **Always Run `timeline_report`**: After modifying scenes, call `timeline_report` to ensure score >= 80 and zero fatal validation errors before requesting Gate 2 review.
