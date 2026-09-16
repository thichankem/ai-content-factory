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

- Documentation and skill files are written in English.
- Skills live in `.claude/skills/<name>/SKILL.md` with YAML frontmatter
  (`name`, `description`, optional `allowed-tools`).
- Configuration templates belong in `.env.example`; never commit a real
  `.env`.
- Keep agent-facing instructions in the skills; keep the overall picture in
  `README.md`.
- The state machine in `src/content_factory/state.py` is authoritative — do
  not bypass it in the service layer.

## Workflow

- To add or change a skill, edit the matching `SKILL.md` and keep the
  frontmatter description accurate.
- After editing Python code, run the quality gates:
  `python -m ruff check src tests`, `python -m ruff format --check src tests`,
  `python -m mypy src`, and `python -m pytest`.
- Before reporting a large task done, run the smoke test: `scripts/smoke.ps1`
  (Windows) or `scripts/smoke.sh` (Linux/macOS/WSL).
- Do not invent files or commands that do not exist yet. If a step depends on
  unimplemented infrastructure, mark it as planned.