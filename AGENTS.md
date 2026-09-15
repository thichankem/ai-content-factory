# AGENTS.md

Guidance for AI coding agents working in this repository.

## What this repo is

A **design specification + agent skills** repository for the AI Content
Factory — an AI-assisted short-form video pipeline with two mandatory human
review gates (script approval, final video approval).

**There is no application code yet.** The backend (`src/content_factory`),
frontend (`frontend/`), helper scripts (`scripts/`), test suite (`tests/`),
packaging (`pyproject.toml`), and design documents (`docs/`) are planned but
not implemented.

## Conventions

- Documentation and skill files are written in English.
- Skills live in `.claude/skills/<name>/SKILL.md` with YAML frontmatter
  (`name`, `description`, optional `allowed-tools`).
- Configuration templates belong in `.env.example`; never commit a real
  `.env`.
- Keep agent-facing instructions in the skills; keep the overall picture in
  `README.md`.

## Workflow

- To add or change a skill, edit the matching `SKILL.md` and keep the
  frontmatter description accurate.
- Do not invent files or commands that do not exist yet. If a step depends on
  unimplemented infrastructure, mark it as planned.