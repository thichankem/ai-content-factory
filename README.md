# AI Content Factory

Design specification and agent skills for an AI-assisted short-form video
production pipeline with two mandatory human review gates: **script approval**
and **final video approval**.

The goal of the project is to turn reference material into a new work: AI may
learn the topic, facts, narrative pacing, and insights from a source, but must
not reproduce the source's script, visuals, voice, or music verbatim without
the right to use them.

## Repository status

**Specification + agent skills only.** This repository currently contains the
design intent and the operational skills, not the application itself.

Planned but **not yet implemented**:

- FastAPI backend under `src/content_factory` (project CRUD, script
  generation, approval gates, generation state machine)
- Vanilla-JS frontend served at `/`
- Helper scripts under `scripts/` (`setup`, `dev`, `test`, `lint`,
  `typecheck`, `smoke`)
- Packaging (`pyproject.toml`), test suite under `tests/`, and CI quality
  gates (ruff + mypy + pytest)
- Design documents under `docs/` (see the planned reading order below)

Until the backend exists, the skills document the **target workflow** and
cannot be executed.

## Repository layout

```
.
├── .claude/
│   ├── settings.json          # Claude Code permission rules
│   └── skills/                # Agent skills (operational playbooks)
│       ├── approve-script/
│       ├── create-project/
│       ├── generate-script/
│       ├── lint/
│       ├── run-dev/
│       ├── smoke-test/
│       └── test/
├── .codex/
│   └── config.toml            # Codex CLI sandbox / approval policy
├── .env.example               # Configuration template (copy to .env)
├── AGENTS.md                  # Guidance for AI coding agents
└── README.md
```

## Skills

| Skill             | Purpose                                                              |
| ----------------- | -------------------------------------------------------------------- |
| `create-project`  | Create a project via `POST /projects`                                |
| `generate-script` | Request an AI script draft via `POST /projects/{id}/script/generate` |
| `approve-script`  | Pass the script approval gate and start generation                   |
| `run-dev`         | Start the dev server (FastAPI + frontend) at `http://127.0.0.1:8080` |
| `test`            | Run the pytest suite                                                 |
| `lint`            | Run the ruff + mypy quality gates                                    |
| `smoke-test`      | Drive the full lifecycle end-to-end over HTTP                        |

## Planned reading order (design docs)

These documents are planned deliverables and are not yet authored:

1. Project Charter
2. Requirements
3. System Architecture
4. End-to-End Pipeline
5. Data Model
6. AI Provider Catalog
7. UI and User Flow
8. Content Quality and Compliance
9. Configuration and Operations
10. Proposed Project Structure
11. Testing Strategy
12. Roadmap
13. OSS Integration Research

New architecture decisions are recorded using the ADR template.

## Local development (target)

Once the backend is implemented:

```powershell
python -m pip install -e ".[dev]"
python -m pytest -q
python -m ruff check src tests
python -m mypy src
uvicorn content_factory.api:app --app-dir src --reload --port 8080
```

API docs: `http://127.0.0.1:8080/docs`.

## Using the API

The skills target a dev server at `http://127.0.0.1:8080`. On Windows
PowerShell, call the real binary as `curl.exe` — the bare `curl` alias maps to
`Invoke-WebRequest`, which does not understand the `-X`/`-H`/`-d` flags used in
the skills.