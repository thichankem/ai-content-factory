---
name: ai-agent-orchestrator
description: AI Agent Skill for multi-agent task distribution and orchestration: routing research to Gemini, viral scripts to Claude, timeline structure to Codex, and logic/fact audits to DeepSeek via the Agent Bridge.
allowed-tools:
  - run_command
  - view_file
  - replace_file_content
---

# AI Agent Orchestrator Skill — Multi-Agent Ensemble

This skill guides orchestrator agents in distributing pipeline tasks across specialized AI model vendors according to their architectural strengths.

## 1. Vendor Role Assignment

- **Google Gemini 2.0 / 1.5 Pro**:
  - **Specialty**: Multimodal vision, massive context window, live web grounding.
  - **Pipeline Role**: Grounded reference research, academic paper summarization, video framing suggestions, b-roll keyword tagging.
- **Anthropic Claude 3.5 Sonnet**:
  - **Specialty**: Nuanced natural language, viral hook engineering, human-like voice rhythm.
  - **Pipeline Role**: Script drafting, section rewriting, emotional hook crafting, narrative polishing.
- **OpenAI Codex / GPT-4o**:
  - **Specialty**: Strict JSON adherence, code-level precision, spatial coordinate math.
  - **Pipeline Role**: Scene breakdown generation, keyframe motion calculation, timeline structural edits.
- **DeepSeek V3 / R1**:
  - **Specialty**: Deep mathematical reasoning, rigorous chain-of-thought, hallucination suppression.
  - **Pipeline Role**: Fact verification, copy-risk plagiarism auditing, logical flow validation.
- **Deterministic Local Engine**:
  - **Specialty**: Zero-latency, zero-cost, privacy-safe, deterministic execution.
  - **Pipeline Role**: Edge-TTS Vietnamese neural voiceover, WebM video export, offline template fallback.

## 2. Agent Bridge Markdown Handoff Workflow

1. **Generate Project Brief**:
   ```bash
   curl -s http://127.0.0.1:8000/projects/<ID>/brief.md?agent=claude > brief.md
   ```
2. **Dispatch Brief to Target Agent** (Claude Code, Gemini CLI, Cursor, etc.).
3. **Receive Agent Output** containing fenced blocks (`script`, `json scenes`, `json style`).
4. **Import Result back into Pipeline**:
   ```bash
   curl -s -X POST http://127.0.0.1:8000/projects/<ID>/agent-result \
     -H 'Content-Type: application/json' \
     -d "{\"markdown\": \"$(cat reply.md)\", \"agent\": \"claude-sonnet\"}"
   ```
