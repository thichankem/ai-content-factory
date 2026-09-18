# Runtime Persistence & Storage: `storage/`

Runtime artifacts for the **AI Content Factory**: uploaded media, content-addressed caches, and the provenance audit log.

---

## Directory layout

```text
storage/
├── uploads/{project_id}/   # Raw user uploads, served as static files at /uploads
├── cache/                  # Content-addressed execution checkpoints (created on first use)
└── audit/                  # Append-only provenance log: audit.jsonl (created on first use)
```

Only `uploads/` exists in a fresh checkout — and only after the first upload or the first test run. `cache/` and `audit/` are created by the code that needs them:

| Setting (`config.py`) | Default | Created by |
| :--- | :--- | :--- |
| `uploads_dir` | `./storage/uploads` | `api/app.py` on startup, and the external-ingest and media routers |
| `cache_dir` | `./storage/cache` | `cache.py` on first checkpoint |
| `audit_dir` | `./storage/audit` | `audit.py::AuditLog.__init__` (`mkdir(parents=True, exist_ok=True)`) |

`.gitignore` excludes `storage/*` — everything here is reproducible and none of it belongs in the repository.

---

## Storage subsystems

### 1. User uploads (`storage/uploads/`)

- One directory per project, keyed by project id.
- Served read-only through `app.mount("/uploads", StaticFiles(...))`, so the studio preview canvas can play a clip straight from disk.
- Written by `POST /projects/{id}/external/upload` and `POST /media/upload`.

**Test artifacts.** `tests/test_external_ingest.py` writes a 31-byte placeholder JPEG (`iceberg_night.jpg`, the bytes `b"FAKE_MP4_VIDEO_HEADER_123456789"`) into a new UUID directory on every run. Each run leaves one behind, and because `storage/*` is gitignored they will not be committed — but they accumulate. Removing them is always safe; the directory itself is recreated at startup.

### 2. Content-addressed cache (`storage/cache/`)

Expensive computations — audio transcription, frame vision scoring, scene-boundary analysis — are keyed by a deterministic hash of their inputs. A retried pipeline or a crashed run resumes from the existing checkpoint instead of redoing the expensive step.

### 3. Provenance audit log (`storage/audit/audit.jsonl`)

Append-only JSON Lines, one `AuditEntry` per line: `ts`, `actor`, `action`, `project_id`, `media_id`, `prompt`, `detail`. `AuditLog.record` appends under a re-entrant lock; `AuditLog._read_valid` tolerates a missing file and skips corrupt lines rather than failing the read.

The log is read through `GET /audit`, and `services/qa.py::_audit_row` derives a `sha256_hash` and a short `id` from each entry's own content before returning it. The hash is computed by the server — a client displaying it is showing a real value, not a decoration.

---

## Where projects live — and don't

**`content_factory/store.py` keeps projects in memory.** It is a thread-safe dictionary (`dict[str, Project]` behind an `RLock`) with compare-and-save via `save_if_unchanged` to catch concurrent writers.

There is **no `projects.json`, no database, and no cross-restart persistence**. Restarting the server discards every project; the audit log survives, but the things it refers to do not.

If durable projects are wanted, that is a new piece of work — a store implementation behind the same interface — not a configuration flag. Earlier documentation in this directory described a `LocalProjectStore` persisting `storage/projects.json`; that component does not exist in the tree.
