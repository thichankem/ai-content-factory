# AGENTS.md

Guidance for AI coding agents working in this repository.

## What this repo is

The **AI Content Factory** — an AI-assisted short-form video pipeline with two
mandatory human review gates (script approval, final video approval).

The full pipeline is implemented: a FastAPI backend
(`src/content_factory`), a vanilla-JS frontend (`frontend/`), a pytest suite
(`tests/`), helper scripts (`scripts/`), and CI (`.github/workflows/ci.yml`).
It covers project creation, AI script drafting (with a built-in offline
template provider), the mandatory script approval gate, a simulated production
worker, the mandatory final-video approval gate, and publishing. The design
documents under `docs/` and real video rendering / publishing integrations are
still planned.

## Conventions

- Documentation and skill files are written in English. The one exception is
  `docs/KE-HOACH-TONG-THE.md`, the operator's master plan, which is kept in
  Vietnamese because the operator writes in Vietnamese.
- Skills live in `.claude/skills/<name>/SKILL.md` with YAML frontmatter
  (`name`, `description`, optional `allowed-tools`).
- Configuration templates belong in `.env.example`; never commit a real
  `.env`.
- Keep agent-facing instructions in the skills; keep the overall picture in
  `README.md`.
- The state machine in `src/content_factory/state.py` is authoritative — do
  not bypass it in the service layer.
- Source rights are never auto-confirmed, by any code path, for any provider
  or external agent.

## Read this first

`docs/KE-HOACH-TONG-THE.md` is the project's memory: the operator's
requirements, the target architecture, the roadmap phases, the open decisions,
and a change log. Read it before starting work and update it when you finish,
following the template at the bottom of that file.

`docs/TOOLCHAIN.md` lists the optional local media/AI tools;
`scripts/toolcheck.py` reports which are actually installed.
`docs/AGENT-BRIDGE.md` documents the Markdown contract used with external AI
agents (Claude Code, Codex, DeepSeek, Gemini).

## Workflow

- To add or change a skill, edit the matching `SKILL.md` and keep the
  frontmatter description accurate.
- Anything the operator can tune belongs in a preset file (`presets/*.json`,
  `presets/*.md`) or an environment variable — not as a constant in code.
  `src/content_factory/presets.py` and `script_engine.py` are the reference
  examples.
- After editing Python code, run the quality gates:
  `python -m ruff check src tests`, `python -m ruff format --check src tests`,
  `python -m mypy src`, and `python -m pytest`.
- Before reporting a large task done, run the smoke test: `scripts/smoke.ps1`
  (Windows) or `scripts/smoke.sh` (Linux/macOS/WSL).
- Do not invent files or commands that do not exist yet. If a step depends on
  unimplemented infrastructure, mark it as planned.