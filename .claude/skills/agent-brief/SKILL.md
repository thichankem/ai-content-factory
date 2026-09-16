---
name: agent-brief
description: >-
  Hand a project to an external AI agent (Claude Code, Codex, DeepSeek, Gemini,
  Cursor, or a human) using a self-contained Markdown brief, then import the
  agent's reply back into the pipeline. Use when the user asks to edit or
  rewrite a script with an outside agent/model, to tune the scripting preset,
  or to inspect what the script linter found.
---

# Work with an external AI agent

The factory does not care which agent writes the script. `brief.md` carries
every piece of context the agent needs; `agent-result` imports its reply. See
`docs/AGENT-BRIDGE.md` for the full contract.

## 0. See what is available

```bash
curl -s http://127.0.0.1:8080/agents
```

Returns `strategy`, `tts_engine`, the enabled `agents` (name, kind, tier,
model, breaker state), and `preset_styles`. Use it to confirm whether Claude,
Gemini, DeepSeek, or a local model is configured before generating in-house.

## 1. Inspect the script before touching it

```bash
curl -s -X POST http://127.0.0.1:8080/projects/<PROJECT_ID>/script/analyze \
  -H 'Content-Type: application/json' -d '{}'
```

Returns `plan` (per-section `estimated_seconds`, `fits_target`, `warnings`)
and `issues` (`code`, `severity`, `message`, `hint`) plus a 0–100 `score`.
Findings to watch for:

- `copy_risk` — **error**: the script reproduces a research source verbatim.
  Fix this before approving.
- `weak_hook`, `long_sentence`, `banned_phrase` — the preset's style contract.
- `timing` — narration is more than 15% off the target duration.

## 2. Export the brief and hand it to the agent

```bash
curl -s http://127.0.0.1:8080/projects/<PROJECT_ID>/brief.md -o brief.md
```

The file already ends with its own "How to reply" contract. Give the agent
that file and ask it to write `reply.md`:

```bash
claude "Read brief.md and follow its 'How to reply' section. Write reply.md."
codex exec "Read brief.md, write reply.md per its reply contract."
```

## 3. Import the reply

```bash
curl -s -X POST http://127.0.0.1:8080/projects/<PROJECT_ID>/agent-result \
  -H 'Content-Type: application/json' \
  -d "{\"markdown\": $(python -c 'import json;print(json.dumps(open("reply.md",encoding="utf-8").read()))'), \"agent\": \"claude-code\"}"
```

The reply may contain any subset of:

- ```` ```script ```` — replaces the narration.
- ```` ```json scenes ```` — merges scene text/narration into the timeline.
- ```` ```json style ```` — validated, saved under `presets/`, and assigned.

HTTP 409 means the project is past `script_review`; a script can only be
imported while the project is `draft` or `script_review`.

## Guarantees to respect

- Source rights are **never** auto-confirmed by an import. A human must still
  confirm rights and pass the script gate.
- After import the service recomputes the timing plan and linter findings.
- Invalid JSON in a block is reported in the returned notes, never fatal.

## Tuning the preset instead

Style presets are plain files — edit them directly or through the API:

```bash
curl -s http://127.0.0.1:8080/script/styles                    # list
curl -s http://127.0.0.1:8080/script/styles/story/md           # read as Markdown
curl -s -X PUT http://127.0.0.1:8080/script/styles/my-style \
  -H 'Content-Type: application/json' -d @presets/vietnamese-short.json
curl -s -X PUT http://127.0.0.1:8080/projects/<PROJECT_ID>/script/style \
  -H 'Content-Type: application/json' -d '{"style":"my-style"}'
```

On Windows PowerShell use `curl.exe` instead of `curl`.
