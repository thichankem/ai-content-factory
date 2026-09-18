# Backend Source Architecture (`src/`)

This directory contains the Python source code for the **AI Content Factory** backend service, internal pipelines, domain models, and API layers.

---

## Package Overview

The primary package is `content_factory` (`src/content_factory/`):

```text
src/
└── content_factory/            # Authoritative domain package
    ├── __init__.py             # Version and package exports
    ├── config.py               # Pydantic Settings with CONTENT_FACTORY_ env prefix
    ├── state.py                # Authoritative state machine & transition validator
    ├── text.py                 # Shared tokenizers, slugs and title keys
    ├── models/                 # Pydantic contracts, split by concern
    │   ├── common.py           # Timestamps, lifecycle enums, health payload
    │   ├── project.py          # Project aggregate and lifecycle payloads
    │   ├── timeline.py         # Scenes, effects, keyframes, render plan
    │   ├── script.py           # Script planning, linting, styles
    │   ├── knowledge.py        # Knowledge base, chunks, retrieval, grounding
    │   └── ...                 # agent, workflow, campaign, external, history, media
    ├── services/               # Service layer: one cohesive mixin per domain
    │   ├── context.py          # ServiceContext: settings, store, lifecycle, worker
    │   ├── projects.py         # Project lifecycle, approvals, publishing
    │   ├── knowledge.py        # Knowledge bases: chunking, retrieval, grounding
    │   ├── timeline.py         # Video NLE operations and render plans
    │   └── ...                 # research, scripting, styles, agents, voice, media,
    │                           # production, workflow, growth, history
    ├── service.py              # Compatibility facade over services/
    ├── script_engine.py        # Rule-based script generation & style preset compiler
    ├── nl_timeline.py          # AI Co-Pilot natural language timeline command parser
    ├── timeline.py             # NLE timeline operations (cuts, speed, ripple edits)
    ├── media.py                # Media intelligence, dHash deduplication, metadata
    ├── api/                    # FastAPI HTTP application & modular routers
    └── ...
```

---

## Design Principles

1. **State Machine Authority**:
   All lifecycle mutations (`draft` -> `script_review` -> `script_approved` -> `generating` -> `video_review` -> `video_approved` -> `published`) are validated exclusively in `src/content_factory/state.py`. The service layer must never bypass these guards.
2. **Two Mandatory Human Review Gates**:
   - **Gate 1 (Script Approval)**: Human operator must confirm source rights and approve the drafted script before generation begins.
   - **Gate 2 (Video Approval)**: Human operator must review and approve the rendered video project before publishing is permitted.
   - External AI agents and automated pipelines are prohibited from auto-confirming source rights or bypassing approvals.
3. **Offline-First Default**:
   All core capabilities (script drafting, timeline mutation, QA checks, accessibility simplification, rule-based heuristics) operate deterministically offline without external API dependencies.
4. **Clean Layer Separation**:
   - `models/`: immutable data structures and validation schemas, grouped by domain.
   - `state.py`: pure state transition functions and error definitions.
   - `services/`: one mixin per domain, composed into `ContentFactoryService`. A mixin
     inherits the layers it calls, so the dependency direction is visible in the class
     header instead of being hidden in a 2000-line file.
   - `api/`: HTTP transport adapters, request validation, and routing.
5. **One Implementation Per Idea**:
   Shared helpers (tokenizers, slugs, title keys, HTTP error mapping) live in exactly
   one module. `tests/test_architecture.py` fails the build if a module grows past the
   line budget, if two mixins define the same method, or if a mixin method is
   unreachable from the composed service.

---

## Code Quality & Standards

Every change within `src/` must satisfy all repository quality gates:

```bash
python -m ruff check src tests scripts
python -m ruff format --check src tests scripts
python -m mypy src
python -m pytest
```
