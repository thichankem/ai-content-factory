# HTTP API Layer: `content_factory.api`

The `src/content_factory/api` package exposes the complete backend surface through FastAPI HTTP endpoints, RESTful JSON contracts, and static web asset mounts.

---

## Architecture & Router Hierarchy

The application entry point is [`app.py`](app.py) (`create_app()`). Routes are partitioned into **19 feature routers** under `routers/`:

```text
src/content_factory/api/
├── __init__.py             # Exports create_app and the default app instance
├── app.py                  # FastAPI factory, exception handlers, static mounts
├── deps.py                 # Error-mapping guards (get_or_404, guard, guard_value)
└── routers/                # 19 feature-specific routers
    ├── health.py           # Health checks and provider availability status
    ├── projects.py         # Project CRUD, research trigger, script save/review, approvals
    ├── timeline.py         # NLE timeline mutations and AI-assist polish
    ├── media.py            # Universal media library: upload, metadata, transcribe, re-cook, delete
    ├── studio_media.py     # Canvas audio/video streaming and asset serving
    ├── external.py         # External asset import (Kling, Suno, Runway) and links
    ├── workflow.py         # Visual DAG orchestrator, checklist, background runner
    ├── campaign.py         # Multi-short campaign generation and asset package export
    ├── qa.py               # Platform/brand/copyright verdicts, audit trail, cost check, Co-Pilot command
    ├── seo.py              # 70-signal scoring, optimiser, A/B plan, keyword mining
    ├── styles.py           # Style preset listing, JSON/MD export, override management
    ├── agents.py           # External agent catalogue and Markdown contract briefs
    ├── library.py          # Document index, BM25 text search, file ingest
    ├── knowledge.py        # Curated knowledge base inspection and topic queries
    ├── history.py          # Edit history and revision snapshots
    ├── graphics.py         # Poster and overlay graphic generators
    ├── resources.py        # Hardware/compute discovery and admission state
    ├── tools.py            # Agent tool registry: GET /tools, POST /tools/call
    └── index.py            # Studio entry point — serves the vanilla dashboard at /
```

> `tools.py` is **not** a system-inspection endpoint. `GET /tools` returns the
> self-describing agent tool manifest and `POST /tools/call` executes one named
> tool — that is the surface `docs/TOOLS-FOR-AGENTS.md` documents. `toolcheck`
> style inspection of local media binaries lives in `scripts/toolcheck.py` and is
> not exposed over HTTP.

---

## Route Ordering Precedence Note

> [!IMPORTANT]
> When mounting sub-routers in `app.py`, sub-routers with static sub-paths (such as `qa.py` with `GET /media/search`) **must** be registered before wildcard path routers (such as `media.py` with `GET /media/{media_id}`). This prevents wildcard path capture collisions.

---

## Request and service boundaries

QA request contracts live in `models/qa.py` and are re-exported by `models`.
The QA router delegates its 13 endpoints to `services/qa.py`; orchestration,
audit persistence, cost calculation and media-engine calls belong to the service.
`POST /timeline/command` remains a preview transformation, not a persisted edit
or an approval. SEO mapping callers and HTTP requests share the input models in
`models/seo.py`; invalid boolean/numeric inputs are no longer silently coerced
by a second service-level parser. `caption_source` now round-trips through both.

## Common Error Handling & Guards

Defined in [`deps.py`](deps.py):

All guards share one mapper, `_http_error`, so the status-code policy exists in a single place: `NotFoundError` to 404, `StateConflictError` and `RightsNotConfirmedError` to 409.

- `_http_error(exc, detail=None)`: the only place that decides a domain error's HTTP status.
- `get_or_404(service, project_id)`: Raises HTTP 404 with the generic `Project not found` detail.
- `guard(fn)`: Wraps project-scoped service calls; the 404 keeps the generic detail so internal ids are not echoed.
- `guard_value(fn)`: Maps domain errors while preserving the service message (used by scene/chunk-level endpoints, where the id *is* the message).
- `guard_await(value)`: The async counterpart of `guard_value`.
- `validation_handler` in `app.py`: Standardizes FastAPI `RequestValidationError` responses to HTTP 422 with structured field issues.

---

## Static Mounts

- `/uploads`: Mounted to `storage/uploads` for user-uploaded raw video, audio and images.
- `/assets`: Mounted to the `frontend/` directory for CSS, JavaScript and static media files.
- `/`: Handled by `index.py`, returning the **vanilla-JS studio dashboard** (`frontend/index.html`).

> The Next.js client under `frontend/src/` is **not** mounted, proxied or served by
> this application. It runs on its own dev server at `http://localhost:3000` and
> forwards `/api/*` to port 8000. See the root `README.md` → “Two frontends”.
