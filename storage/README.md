# Runtime Persistence & Storage: `storage/`

This directory manages application runtime state, project database files, uploaded media, and content-addressed cache checkpoints for the **AI Content Factory**.

---

## Directory Organization

```text
storage/
├── cache/              # Content-addressed execution checkpoints (by input hash)
├── uploads/            # Raw user uploads (mounted at /uploads in FastAPI)
├── media/              # Rendered intermediate media and temporary working clips
└── projects.json       # (Default) Local JSON store persisting Project entities
```

---

## Storage Subsystems

1. **Content-Addressed Cache (`storage/cache/`)**:
   - Expensive computations (audio transcription, frame vision scoring, scene boundary analysis) are cached using deterministic cryptographic hashes of their inputs.
   - Retried pipelines and crash recovery resume directly from existing checkpoints instead of repeating computationally heavy tasks.
2. **User Uploads (`storage/uploads/`)**:
   - Dedicated storage directory for media uploaded through HTTP API endpoints.
   - Mounted as static files via `app.mount("/uploads", StaticFiles(...))` for immediate playback in the studio preview canvas.
3. **Project Persistence**:
   - Project definitions, scripts, timing plans, review statuses, and approval records persist within `projects.json` via `LocalProjectStore`.
