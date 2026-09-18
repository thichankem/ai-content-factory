# HTTP API Layer: `content_factory.api`

The `src/content_factory/api` package exposes the complete backend surface through FastAPI HTTP endpoints, RESTful JSON contracts, and static web asset mounts.

---

## Architecture & Router Hierarchy

The application entry point is [`app.py`](file:///c:/Users/ADMIN/OneDrive/M%C3%A1y%20t%C3%ADnh/GitHub/ai-content-factory/src/content_factory/api/app.py) (`create_app()`). Routes are partitioned into dedicated sub-routers under `routers/`:

```text
src/content_factory/api/
├── __init__.py             # Exports create_app and default app instance
├── app.py                  # FastAPI factory, exception handlers, static mounts
├── deps.py                 # Error-mapping guards (get_or_404, guard, guard_value)
└── routers/                # 17 Feature-specific sub-routers
    ├── health.py           # Health checks and provider availability status
    ├── qa.py               # Platform compliance, brand kit, audit trail, Co-Pilot command
    ├── projects.py         # Project CRUD, research trigger, script review, approvals
    ├── styles.py           # Style presets listing, JSON/MD export, override management
    ├── agents.py           # External agent catalog and Markdown contract briefs
    ├── library.py          # Document index, BM25 text search, file ingest
    ├── timeline.py         # NLE video-project timeline mutations and AI-assist polish
    ├── workflow.py         # Visual DAG workflow orchestrator, checklist, background runner
    ├── campaign.py         # Multi-short campaign generation and asset package export
    ├── knowledge.py        # Curated knowledge base inspection and topic queries
    ├── studio_media.py     # Canvas audio/video streaming and asset serving
    ├── media.py            # Universal media library upload, metadata, and deletion
    ├── tools.py            # System toolcheck status and media CLI inspection
    ├── external.py         # External asset import (Kling, Suno, Runway) and links
    ├── history.py          # Edit history and revision snapshots
    ├── graphics.py         # Poster and overlay graphic generators
    └── index.py            # Studio SPA entry point (serves dashboard HTML)
```

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

Defined in [`deps.py`](file:///c:/Users/ADMIN/OneDrive/M%C3%A1y%20t%C3%ADnh/GitHub/ai-content-factory/src/content_factory/api/deps.py):

All guards share one mapper, `_http_error`, so the status-code policy exists in a single place: `NotFoundError` to 404, `StateConflictError` and `RightsNotConfirmedError` to 409.

- `_http_error(exc, detail=None)`: the only place that decides a domain error's HTTP status.
- `get_or_404(service, project_id)`: Raises HTTP 404 with the generic `Project not found` detail.
- `guard(fn)`: Wraps project-scoped service calls; the 404 keeps the generic detail so internal ids are not echoed.
- `guard_value(fn)`: Maps domain errors while preserving the service message (used by scene/chunk-level endpoints, where the id *is* the message).
- `guard_await(value)`: The async counterpart of `guard_value`.
- `validation_handler` in `app.py`: Standardizes FastAPI `RequestValidationError` responses to HTTP 422 with structured field issues.

---

## Static Mounts

- `/uploads`: Mounted to `storage/uploads` for user-uploaded raw video, audio, and images.
- `/assets`: Mounted to `frontend/` directory for CSS, JavaScript, and static media files.
- `/`: Handled by `index.py` returning the studio Single Page Application dashboard.
