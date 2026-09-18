# External AI agent bridge

The factory never assumes it is the only writer. Any AI agent — Claude Code,
Codex, DeepSeek, Gemini, Cursor, or a human at a terminal — can pick up a
project, edit it, and hand the result back through one plain-Markdown
contract.

## Why Markdown

- It survives copy/paste into any chat window or CLI agent.
- It round-trips: the brief contains the reply format, so the agent does not
  need extra instructions.
- It is diffable and reviewable by a human before anything is applied.
- It keeps generated content (the `script` block) separate from metadata
  (`json style`, `json scenes`), so a partial answer is still valid.

## Flow

```
GET  /projects/{id}/brief.md          -> paste this into the agent
     (agent does the work, replies with fenced blocks)
POST /projects/{id}/agent-result      -> { "markdown": "<the reply>", "agent": "claude-code" }
```

```bash
curl -s http://127.0.0.1:8080/projects/<ID>/brief.md > brief.md
# ... hand brief.md to the agent, save its reply as reply.md ...
curl -s -X POST http://127.0.0.1:8080/projects/<ID>/agent-result \
  -H 'Content-Type: application/json' \
  -d "$(python -c 'import json,sys;print(json.dumps({"markdown":open("reply.md",encoding="utf-8").read(),"agent":"claude-code"}))')"
```

## What the brief contains

1. YAML front matter: project id, topic, language, target duration, status,
   style, agent hint, and timestamp.
2. The mission: original narration, target language, target runtime, and the
   "transform, do not copy" rule.
3. The full style contract of the project's preset.
4. Reference material and key facts (or an explicit "no research" note).
5. The current script in a `script` fenced block.
6. Automatic analysis: estimated runtime, readiness score, and every linter
   finding with hints.
7. The scene timeline table, when a video project exists.
8. The reply contract.

## Reply contract

Return only what you changed, as fenced blocks. The narration block comes
first.

````markdown
```script
[Hook]
The city whispers before it wakes.

[Turn]
Trucks and shutters are the only choir.
```

```json scenes
[{"label": "Hook", "text": "5am", "narration": "The city whispers before it wakes."}]
```

```json style
{"name": "my-style", "tone": "hushed", "sentence_max_units": 10}
```
````

| Block | Required | Effect |
| ----- | -------- | ------ |
| ```` ```script ```` | no | Replaces the narration. Section markers preserved. |
| ```` ```json scenes ```` | no | Merges `label` / `text` / `narration` / `background` into the timeline by index, then re-fits durations. |
| ```` ```json style ```` | no | Validated as a preset, saved under `presets/`, and assigned to the project. |

Fence info strings are forgiving: `` ```json script ``, `` ```scenes `` and
`` ```json `` (auto-classified by payload shape) all work. Invalid JSON never
crashes the pipeline — it lands in the returned notes instead.

An unfenced reply still works if it contains `[Section]` markers.

## Guarantees

- **Rights are never auto-confirmed.** Importing a script always resets
  `source_rights_confirmed` to `false`, so a human must still pass the script
  gate.
- **Imports are state-checked.** A script can only be imported while the
  project is in `draft` or `script_review`; otherwise the call returns HTTP
  409.
- **Everything is re-analyzed.** After an import the service recomputes the
  timing plan and linter findings, so the UI shows fresh numbers immediately.
- **Web access is unnecessary.** The brief is self-contained; the agent does
  not need to call the API.

## Wire it to a local agent

Any agent that can read a file, call an MCP tool, or interact via CLI is supported:

```bash
# 1. Google Antigravity (with Multimodal AI Vision)
# Antigravity reads brief.md, inspects keyframes/contact sheets visually via view_file, and outputs reply.md:
agy "Read brief.md, inspect the video frames visually, follow the reply contract, and write reply.md."

# 2. Claude Code
claude "Read brief.md and follow its 'How to reply' section. Write reply.md." \
  && echo "done"

# 3. Codex CLI
codex exec "Read brief.md, write reply.md per its reply contract."

# 4. Cursor / Windsurf
# Use .cursorrules or open brief.md and ask the agent to format its reply in reply.md.

# 5. Gemini CLI / DeepSeek
gemini "Read brief.md and produce reply.md matching the fenced block contract."
```

## Agent Capabilities Matrix

| AI Agent | Integration Method | Skills Location | AI Vision Support | Tool Calling Format |
| :--- | :--- | :--- | :---: | :--- |
| **Google Antigravity** | `.agents/`, MCP, `/tools/call` | `.agents/skills/` | 👁️ **Native (Multimodal)** | Direct tool calls + Visual frame QA |
| **Claude Code** | `.claude/skills/`, `/tools/call` | `.claude/skills/` | 📷 Via image tools | Shell curl / MCP stdio |
| **Cursor / Windsurf** | `.cursorrules`, MCP server | Workspace Root | 📷 Via editor image preview | MCP server (`mcp_config.json`) |
| **OpenAI / Codex** | Markdown Bridge / API | `brief.md` / `agent-result` | ❌ Text-first heuristics | REST JSON Schema |
| **Gemini CLI / DeepSeek** | HTTP `/tools/call` / Markdown | `brief.md` / API | 📷 Model dependent | REST / JSON |

For a fully automatic loop, poll `/projects` for `script_review`, fetch each
brief, run the agent, and POST the reply back to `/agent-result`.

