# Backend Source Architecture (`src/`)

This directory contains the Python source code for the **AI Content Factory** backend: the domain package, its internal pipelines, the FastAPI layer, and the test-facing contracts.

---

## Package Overview

The single package is `content_factory`. It currently holds **51 top-level modules** plus three sub-packages:

```text
src/
└── content_factory/
    ├── __init__.py             # Version and package exports
    ├── config.py               # Pydantic Settings, CONTENT_FACTORY_ env prefix
    ├── state.py                # Authoritative state machine & transition validator
    ├── text.py                 # Shared tokenizers, slugs, title keys
    ├── store.py                # Thread-safe IN-MEMORY project repository
    │
    ├── models/                 # Pydantic contracts, one module per domain
    │   ├── common.py           # Timestamps, lifecycle enums, health payload
    │   ├── project.py          # Project aggregate and lifecycle payloads
    │   ├── timeline.py         # Scenes, effects, keyframes, render plan
    │   ├── script.py           # Script planning, linting, styles
    │   ├── qa.py               # QA requests, audit entries, cost checks
    │   ├── knowledge.py        # Knowledge bases, chunks, retrieval, grounding
    │   └── …                   # agent, workflow, campaign, external, history, media,
    │                           # seo, voice, research, audio, captions, export_qc, fusion
    │
    ├── services/               # Service layer: one cohesive mixin per domain
    │   ├── context.py          # ServiceContext: settings, store, lifecycle, worker
    │   ├── errors.py           # Domain errors the HTTP layer maps to status codes
    │   ├── projects.py         # Project lifecycle, approvals, publishing
    │   ├── knowledge.py        # Chunking, retrieval, grounding
    │   ├── timeline.py         # NLE operations and render plans
    │   ├── qa.py               # Platform/brand/copyright verdicts, audit, cost
    │   ├── seo.py              # SEO request mapping
    │   └── …                   # research, scripting, styles, agents, voice, media,
    │                           # media_tools, production, workflow, growth, history
    ├── service.py              # Compatibility facade over services/
    │
    ├── seo/                    # SEO engine, split into focused modules
    │                           # (contracts, profiles, signals, scoring,
    │                           #  optimization, experiments, keywords, calibration)
    │
    ├── api/                    # FastAPI application, guards and 19 feature routers
    │   ├── app.py              # create_app(): mounts, exception handlers
    │   ├── deps.py             # get_or_404, guard, guard_value, guard_await
    │   └── routers/            # agents, campaign, external, graphics, health, history,
    │                           # index, knowledge, library, media, projects, qa,
    │                           # resources, seo, studio_media, styles, timeline,
    │                           # tools, workflow
    │
    ├── script_engine.py        # Rule-based script generation & style preset compiler
    ├── nl_timeline.py          # Natural-language timeline command parser (VI/EN)
    ├── scenes.py               # Script → initial editable video project
    ├── timeline.py             # NLE operations, validator, render-plan compiler
    ├── workflow.py             # DAG runner & pre-save checklist
    ├── campaign.py             # Multi-format campaign & prompt matrix
    ├── recook.py               # Re-cook pipeline from an ingested clip
    ├── providers.py            # Multi-vendor AI provider chain & circuit breakers
    ├── research.py / search.py / documents.py / rag.py / library.py
    │                           # Federated research, ranking, chunking, FTS5 index
    ├── media.py / media_tools.py / dedup.py / perception.py / vision.py
    │                           # Media intelligence, dHash, audio & visual perception
    ├── image_engine.py / photo_compositor.py / render.py / thumbnail.py / map_generator.py
    │                           # Image ops, compositing, ffmpeg rendering, graphics
    ├── tts.py / voice_engine.py / audio.py / image_voice_service.py
    │                           # Narration, speech chain, ducking
    ├── compliance.py / audit.py / cost_guard.py / virality.py / sensitivity.py
    │                           # Quality gates, provenance, budget, scoring
    ├── agent_bridge.py / agent_tools.py
    │                           # Markdown briefs + the self-describing tool registry
    ├── cache.py / compute.py / hardware.py / resources.py / resilience.py / sandbox.py
    │                           # Compute discovery, caching, admission control
    └── …                       # on_this_day, presets, smart, simple_subtitles,
                                # ai_video_editor, dedup, fusion_graph
```

---

## Design Principles

1. **State Machine Authority**
   Every lifecycle mutation (`draft` → `script_review` → `script_approved` → `generating` → `video_review` → `video_approved` → `published`) is validated exclusively in `src/content_factory/state.py`. The service layer must never bypass those guards.

2. **Two Mandatory Human Review Gates**
   - **Gate 1 (Script Approval)**: a human operator must confirm source rights and approve the drafted script before generation begins.
   - **Gate 2 (Video Approval)**: a human operator must review and approve the rendered video before publishing is permitted.
   - External AI agents and automated pipelines are prohibited from auto-confirming source rights or bypassing approvals.

3. **Offline-First Default**
   All core capabilities (script drafting, timeline mutation, QA checks, accessibility simplification, rule-based heuristics) operate deterministically offline without external API dependencies.

4. **Clean Layer Separation**
   - `models/`: validation schemas and immutable data structures, grouped by domain.
   - `state.py`: pure transition functions and the error definitions they raise.
   - `services/`: one mixin per domain, composed into `ContentFactoryService`. A mixin inherits the layers it calls, so the dependency direction is visible in the class header instead of being hidden in a 2,000-line file.
   - `api/`: HTTP transport adapters, request validation and routing.

5. **One Implementation Per Idea**
   Shared helpers (tokenizers, slugs, title keys, HTTP error mapping) live in exactly one module. `tests/test_architecture.py` fails the build if a module grows past the line budget, if two mixins define the same method, or if a mixin method is unreachable from the composed service.

6. **Server-Owned Numbers**
   Any figure an operator will act on — readiness scores, verification status, hashes, budgets — is computed by the backend. Clients render it; they do not re-derive or substitute it. `services/qa.py::_audit_row`, for example, derives each audit entry's `sha256_hash` from the entry's own content so the value a client displays is one the server actually computed.

---

## Storage reality

`store.py` is a **process-local, thread-safe dictionary**. There is no `projects.json`, no database, and no cross-restart persistence — projects are lost when the process exits. Anything expecting durable project storage is working from older documentation.

---

## Code Quality & Standards

Every change within `src/` must satisfy all repository quality gates:

```bash
python -m ruff check src tests scripts
python -m ruff format --check src tests scripts
python -m mypy src
python -m pytest
```

Current measured status on this checkout — **these gates are red**, and the numbers are recorded so nobody assumes otherwise:

| Gate | Result |
| :--- | :--- |
| `ruff check src tests scripts` | 242 findings (154 `E501`, 20 `F821`, 8 `E402`, 7 `BLE001`, 6 `PTH202`, …) |
| `ruff format --check src tests scripts` | 13 files would be reformatted |
| `mypy src` | 43 errors in 7 files, out of 129 checked |
| `pytest` | ~634 tests, 11 failing (all for a missing `ffmpeg` on `PATH`) |

The mypy failures cluster in the modules added most recently — `fusion_graph.py`, `photo_compositor.py`, `media_tools.py`, `hardware.py` and `models/{audio,captions,export_qc}.py`. Clear those before treating the checks as a regression signal again.
