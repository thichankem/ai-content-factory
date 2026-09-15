---
name: smoke-test
description: >-
  Verify the whole AI Content Factory still works end-to-end: start (or reuse
  the server), drive the full lifecycle over HTTP, and check the frontend is
  served. Use after API/domain changes, before reporting a large task done,
  or when asked to smoke test.
allowed-tools: "Bash(scripts/smoke.ps1), Bash(scripts/smoke.sh)"
---

# End-to-end smoke test

> **Note:** The backend, frontend, and helper scripts are planned but not yet
> implemented. These steps define the target workflow.

Run the same check that CI runs:

- Windows: `scripts/smoke.ps1`
- Linux/macOS/WSL: `scripts/smoke.sh`

The Python driver (`scripts/smoke.py`) spawns its own uvicorn when nothing
runs on :8080, waits for `/health`, then asserts:

1. `GET /health` returns `ok`
2. `POST /projects` creates a draft project
3. `PUT /projects/{id}/script` + rights → `script_review`
4. `POST /projects/{id}/approvals` → `script_approved`
5. `POST /projects/{id}/generate` → `generating`
6. Final GET confirms the state machine is consistent
7. `GET /` serves the frontend HTML

Exit code 0 = green. On failure, read the stack trace and fix backwards from
the failing step.

(An already-running server on :8080 is reused and left running.)