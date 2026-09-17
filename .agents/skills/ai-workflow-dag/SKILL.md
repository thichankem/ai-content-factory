---
name: ai-workflow-dag
description: AI Agent Skill for building, validating, and executing autonomous video production DAGs (Directed Acyclic Graphs), managing pre-save checklist audits, and orchestrating pipeline nodes.
allowed-tools:
  - run_command
  - view_file
  - replace_file_content
---

# AI Workflow DAG Skill — Graph-Orchestrated Production

This skill enables AI agents to compose, audit, and trigger automated production pipelines structured as Directed Acyclic Graphs (`WorkflowNode` connected by `WorkflowEdge`).

## 1. Supported Block Catalog

Retrieve the palette of available production blocks via `GET /workflow/blocks`:

| Block Type | Label | Role | Required Parameters |
| ---------- | ----- | ---- | ------------------- |
| `research` | Research sources | Gathers reference literature & key facts | None |
| `script` | Draft script | Crafts narration via the AI provider chain | None |
| `lint` | Lint script | Computes quality score & copy-risk findings | None |
| `gate` | Human gate | Mandatory human review gate | `stage`: `"script"` or `"video"` |
| `voiceover` | Narrate scenes | Synthesizes neural TTS voiceover | None |
| `scenes` | Produce video | Builds editable NLE timeline | None |
| `ai_assist` | AI auto-edit | Auto-fits durations, beat sync, styles | None |
| `timeline_check` | Validate cut | Validates contrast, pacing, overflow | None |
| `render_plan` | Compile render plan | Compiles timeline into render plan | None |
| `publish` | Publish | Dispatches approved video to channels | `platforms`: `["youtube", "tiktok"]` |

## 2. Pre-Flight Checklist Audit

Before saving or executing any workflow, always run the pre-save gate:
```bash
curl -s http://127.0.0.1:8000/projects/<PROJECT_ID>/workflow/checklist
```
The checklist enforces:
1. No unreachable nodes.
2. No circular dependencies (DAG property).
3. All required parameters (`stage` for gate, `platforms` for publish) are populated.
4. Two mandatory human review gates (`script` and `video`) are strictly honored and never bypassed.

## 3. Workflow Execution

- Trigger execution: `POST /projects/{id}/workflow/run` with `{"project_id": "...", "background": false}`
- Poll runs: `GET /projects/{id}/workflow/runs`
