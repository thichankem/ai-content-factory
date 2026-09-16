# AI Content Factory

An AI-assisted short-form video production pipeline with two mandatory human
review gates: **script approval** and **final video approval**.

The goal of the project is to turn reference material into a new work: AI may
learn the topic, facts, narrative pacing, and insights from a source, but must
not reproduce the source's script, visuals, voice, or music verbatim without
the right to use them.

## Status

The full pipeline is implemented and green:

- **Backend** — FastAPI application under `src/content_factory` with a project
  lifecycle state machine, an AI provider chain (built-in template + weak
  local tier + strong API tier), a simulated production worker, and both
  mandatory human review gates (script and final video).
- **Frontend** — vanilla-JS dashboard served at `/` that drives the whole
  lifecycle, including a live render-progress bar, video review, and publish.
- **Tests** — 85 pytest tests, ruff + mypy clean, and an end-to-end smoke test
  that drives the pipeline from draft to published.
- **CI** — GitHub Actions workflow running all quality gates.

Still planned (not yet authored): the full design documents under `docs/` and
real video rendering / publishing integrations (the current worker simulates
production).

## Features

- Create and list projects (`name`, `topic`, `target_language`, target
  duration).
- **World-class document search**: a federated search engine queries six real
  public sources concurrently — arXiv, Crossref, Gutenberg, Open Library,
  Wikipedia, and Internet Archive — normalizes them into one rich result type
  (authors, year, abstract, DOI, PDF URL, venue, citations, open-access flag),
  deduplicates, and reranks with a lexical relevance scorer (phrase bonus,
  term coverage, bigram continuity, off-topic penalties). Every result can be
  exported as BibTeX or Markdown.
- **Local document library**: one-click streaming downloads of found documents
  into a persistent library, indexed page-by-page with a SQLite FTS5 BM25
  full-text index — instant ranked search with highlighted snippets across
  everything you download.
- **Research-grounded scripts**: the research engine combines the curated
  reference library with live federated web results, gathering sources (with
  highlights) plus distilled key facts, and grounds the script draft in that
  material. The UI presents it as an LLM-style research notebook.
- Draft a narration script through a **provider chain**: a built-in offline
  template provider first (works with zero configuration), then a
  weak/cheap/local tier, then a strong API tier — with automatic fallback and
  configurable cost-first / quality-first strategies.
- Resilience built in: exponential-backoff retries with jitter, per-provider
  circuit breakers, and a shared token-bucket rate limiter.
- **Simulated production worker**: rendering runs in the background with
  live progress, then builds an **editable scene-based video project** from
  the script and moves the project to video review.
- **Professional video editor** (browser-based, inspired by Shotcut / OpenShot
  / CapCut): multitrack timeline (scenes + text + music), 7 transition types
  (cut, fade, slide, zoom, wipe, circle, dissolve), 10 color filters, 8
  effects (glitch, pixelate, scanlines, film-grain, old-film, dreamy,
  sharpen, mosaic), 5 cinematic color grades (teal-orange, noir, vintage,
  cyberpunk, pastel), keyframe-style motion animation (scale, rotation,
  opacity, position, easing), emoji sticker overlays, Ken Burns pan/zoom, 7
  text styles (title, subtitle, caption, neon, outline, shadow),
  entrance/exit animations, per-scene speed control, aspect-ratio presets
  (9:16 / 16:9 / 1:1 / 4:5), fps (24/30/60), captions, procedural beat music
  (BPM-synced), undo/redo, and **real video export** (canvas → WebM) that
  uploads the finished video to the backend.
- **AI voiceover, perfectly synced**: one click synthesizes narration for
  every scene with Microsoft Edge neural voices via `edge-tts` (free, natural,
  100+ locales including Vietnamese) with `gTTS` as an automatic fallback.
  Each scene's duration is measured from the actual audio and the scene
  timing is adjusted to match it exactly; the narration is played back during
  preview and **captured into the exported WebM as an Opus audio track**
  alongside the VP9 video. Per-scene **voice pitch** control (0.5×–2×) is
  mapped to edge-tts semitone shifts.
- **✨ AI Assist panel** (AI-first editing): one-click auto-edit that fits
  scene durations to text length, snaps scenes to a BPM beat grid, suggests
  the best filter/effect/grade/transition for each scene from its content,
  polishes scene text, and turns narration into auto-captions — all driven by
  the backend `smart.py` intelligence and exposed as REST endpoints.
- Human-in-the-loop guarantees:
  - AI-generated scripts **never** auto-confirm source rights.
  - Production cannot start until a human approves the script **and**
    confirms source rights.
  - Publishing cannot happen until a human approves the final video.
- Full lifecycle state machine:

  ```
  draft → script_review → script_approved → generating → video_review
                                                        ↘ failed → generating (retry)
  video_review → video_approved → published
  video_review → generating (re-render after rejection)
  ```

## Repository layout

```
.
├── .claude/                     # Claude Code permissions + agent skills
│   └── skills/                  # Operational playbooks (see table below)
├── .codex/config.toml           # Codex CLI sandbox / approval policy
├── .github/workflows/ci.yml     # CI quality gates
├── .env.example                 # Configuration template (copy to .env)
├── AGENTS.md                    # Guidance for AI coding agents
├── frontend/                    # Vanilla-JS dashboard (served at /)
│   ├── index.html
│   ├── app.js
│   └── style.css
├── pyproject.toml               # Packaging, ruff, mypy, pytest config
├── scripts/                     # Cross-platform helper scripts
│   ├── setup.ps1 / setup.sh     # Create venv + install dev deps
│   ├── dev.ps1 / dev.sh         # Start the dev server
│   ├── test.ps1 / test.sh       # Run pytest
│   ├── lint.ps1 / lint.sh       # Run ruff + mypy
│   ├── typecheck.ps1 / typecheck.sh
│   └── smoke.ps1 / smoke.sh / smoke.py
├── src/content_factory/         # Backend package
│   ├── api.py                   # FastAPI app + routes
│   ├── config.py                # Settings (CONTENT_FACTORY_* env vars)
│   ├── documents.py             # Federated search + providers + reranker
│   ├── library.py               # BM25 full-text index + streaming downloads
│   ├── models.py                # Domain models
│   ├── providers.py             # Provider chain + OpenAI-compatible adapter
│   ├── research.py              # Research engine + curated reference library
│   ├── resilience.py            # Circuit breaker, token bucket, retry
│   ├── scenes.py                # Script → editable video scenes
│   ├── service.py               # Application service / workflow
│   ├── state.py                 # State machine
│   ├── store.py                 # In-memory project store
│   └── tts.py                   # Text-to-speech engine (edge-tts + gTTS)
└── tests/                       # pytest suite
```

## Quickstart

Requires Python 3.11+.

```powershell
# Windows / PowerShell
python -m pip install -e ".[dev]"
python -m pytest -q
python -m ruff check src tests
python -m mypy src
scripts\dev.ps1
```

```bash
# Linux / macOS / WSL
python3 -m pip install -e ".[dev]"
./scripts/test.sh
./scripts/lint.sh
./scripts/dev.sh
```

Open the UI at `http://127.0.0.1:8080/` and the API docs at
`http://127.0.0.1:8080/docs`.

## API

| Method | Path                              | Description                                  |
| ------ | --------------------------------- | -------------------------------------------- |
| GET    | `/health`                         | Health + provider breaker states             |
| POST   | `/projects`                       | Create a project (201, status `draft`)       |
| GET    | `/projects`                       | List projects                                |
| GET    | `/projects/{id}`                  | Get one project                              |
| POST   | `/projects/{id}/research`        | Gather reference sources + key facts      |
| GET    | `/projects/{id}/research`        | Return the stored research bundle         |
| GET    | `/documents/search`              | Federated search (arXiv, Crossref, …)     |
| POST   | `/projects/{id}/documents`       | Download + index + attach a document      |
| GET    | `/library/search`                | Full-text BM25 search of the library      |
| GET    | `/library`                       | Library listing + index stats             |
| PUT    | `/projects/{id}/script`           | Save script + confirm source rights          |
| POST   | `/projects/{id}/script/generate`  | Draft a script via the provider chain        |
| POST   | `/projects/{id}/approvals`        | Submit a human review decision (script/video)|
| POST   | `/projects/{id}/generate`         | Start/retry/re-render production             |
| GET    | `/projects/{id}/video-project`    | Get the editable scene-based video project   |
| PUT    | `/projects/{id}/video-project`    | Save video editor edits                      |
| POST   | `/projects/{id}/video/upload`     | Upload an exported WebM (multipart)          |
| GET    | `/projects/{id}/video`            | Download the exported video                  |
| POST   | `/projects/{id}/voiceover/generate`| Synthesize narration for every scene         |
| GET    | `/projects/{id}/voiceover/{sid}`   | Download one narration audio clip            |
| POST   | `/projects/{id}/video-project/ai-assist` | Run the AI auto-edit pipeline (fit/beat) |
| GET    | `/projects/{id}/video-project/scenes/{sid}/suggest` | AI look suggestions for a scene |
| POST   | `/projects/{id}/video-project/scenes/{sid}/polish`  | AI-polish a scene's text       |
| POST   | `/projects/{id}/publish`          | Publish an approved video                    |
| GET    | `/projects/{id}/thumbnail`        | Generated SVG thumbnail for the video        |
| GET    | `/`                               | Dashboard HTML                               |

Typical lifecycle:

```bash
curl -s -X POST http://127.0.0.1:8080/projects \
  -H 'Content-Type: application/json' \
  -d '{"name":"Demo","topic":"Morning light","target_language":"vi","duration_target_seconds":45}'

curl -s -X PUT http://127.0.0.1:8080/projects/<ID>/script \
  -H 'Content-Type: application/json' \
  -d '{"script":"Final narration.","source_rights_confirmed":true}'

curl -s -X POST http://127.0.0.1:8080/projects/<ID>/approvals \
  -H 'Content-Type: application/json' \
  -d '{"stage":"script","verdict":"approved"}'

curl -s -X POST http://127.0.0.1:8080/projects/<ID>/generate

# wait for the worker to finish (poll GET /projects/<ID> until video_review)

curl -s -X POST http://127.0.0.1:8080/projects/<ID>/approvals \
  -H 'Content-Type: application/json' \
  -d '{"stage":"video","verdict":"approved"}'

curl -s -X POST http://127.0.0.1:8080/projects/<ID>/publish \
  -H 'Content-Type: application/json' \
  -d '{"platforms":["youtube"]}'
```

On Windows PowerShell, call the real binary as `curl.exe` — the bare `curl`
alias maps to `Invoke-WebRequest`.

## Configuration

Copy `.env.example` to `.env` and adjust. All variables are optional and use
the `CONTENT_FACTORY_` prefix:

- `CONTENT_FACTORY_PROVIDER_STRATEGY` — `cost_first` (default) or
  `quality_first`.
- Weak tier: `CONTENT_FACTORY_MONEY_PRINTER_ENABLED`,
  `CONTENT_FACTORY_MONEY_PRINTER_BASE_URL`.
- Strong tier: `CONTENT_FACTORY_STRONG_LLM_ENABLED`,
  `CONTENT_FACTORY_STRONG_LLM_BASE_URL`, `..._API_KEY`, `..._MODEL`.
- Built-in fallback: `CONTENT_FACTORY_TEMPLATE_ENABLED` (on by default, so the
  pipeline works with no external service).
- Research: `CONTENT_FACTORY_RESEARCH_MAX_SOURCES` (default 6).
- Document search: `CONTENT_FACTORY_DOCUMENTS_WEB_ENABLED` (on by default),
  `CONTENT_FACTORY_DOCUMENTS_SEARCH_TIMEOUT_SECONDS` (default 8).
- Library: `CONTENT_FACTORY_LIBRARY_DIR` (default `./library`),
  `CONTENT_FACTORY_LIBRARY_DB_PATH`.
- Simulated production: `CONTENT_FACTORY_GENERATION_STEPS`,
  `CONTENT_FACTORY_GENERATION_STEP_DELAY_SECONDS`,
  `CONTENT_FACTORY_VIDEO_FORMAT`.
- Voiceover: `CONTENT_FACTORY_TTS_ENABLED`, `CONTENT_FACTORY_TTS_ENGINE`
  (`edge` / `gtts` / `off`), `CONTENT_FACTORY_TTS_VOICE`,
  `CONTENT_FACTORY_TTS_RATE`.
- Resilience: retry, circuit-breaker, and rate-limit tuning.

If every provider is disabled, `POST /projects/{id}/script/generate` returns
HTTP 503 and the system degrades gracefully.

## Skills

Agent skills live in `.claude/skills/<name>/SKILL.md`:

| Skill             | Purpose                                                              |
| ----------------- | -------------------------------------------------------------------- |
| `create-project`  | Create a project via `POST /projects`                                |
| `search-documents`| Federated search across public sources + download into the library   |
| `generate-script` | Request an AI script draft via `POST /projects/{id}/script/generate` |
| `approve-script`  | Pass the script approval gate and start generation                   |
| `edit-video`      | Edit scenes in the video editor and export a real WebM               |
| `review-video`    | Approve/reject the produced video and publish                        |
| `run-dev`         | Start the dev server at `http://127.0.0.1:8080`                      |
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