# Operational Scripts & Tooling: `scripts/`

26 scripts for setup, development, verification, QA, and benchmarking. Two conventions apply throughout:

- **`.ps1` / `.sh` pairs** are thin wrappers around a Python entry point or a single command, so Windows and POSIX stay in step.
- **`qa_*.py` scripts are drivers, not unit tests.** They exercise real media and a live server, and they are not part of `pytest`.

---

## Setup, development and wrappers

| Script | Purpose |
| :--- | :--- |
| [`setup.ps1`](setup.ps1) / [`setup.sh`](setup.sh) | Create the virtualenv, install `.[dev]`, and prepare the workspace |
| [`dev.ps1`](dev.ps1) / [`dev.sh`](dev.sh) | Launch Uvicorn with hot reload (`src/content_factory.api:app`) |
| [`test.ps1`](test.ps1) / [`test.sh`](test.sh) | Run `pytest` |
| [`lint.ps1`](lint.ps1) / [`lint.sh`](lint.sh) | Run `ruff check` + `ruff format --check` |
| [`typecheck.ps1`](typecheck.ps1) / [`typecheck.sh`](typecheck.sh) | Run `mypy src` |
| [`smoke.ps1`](smoke.ps1) / [`smoke.sh`](smoke.sh) | Wrappers for `smoke.py` |

## Verification

| Script | Purpose |
| :--- | :--- |
| [`smoke.py`](smoke.py) | **End-to-end pipeline smoke test.** Drives the full lifecycle (`draft` → `script_review` → `script_approved` → `generating` → `video_review` → `video_approved` → `published`) over real HTTP against a live or spawned server, printing `SMOKE TEST PASSED — N checks` on success. This is the gate that proves the served studio still works, so it is the one to run before concluding a change |
| [`frontend_imports.py`](frontend_imports.py) | **Static import/export checker for the Next.js frontend.** Resolves every import in `frontend/src` to a real file (understanding the `@/` alias and `index.*` barrels), then verifies every named import is actually exported — including `export * as ns`, `export type { … }` and `export { a as b }`. Reports “clean (N files)” and exits non-zero otherwise. Written because the Next client is not type-checked by CI: pure Python, no dependencies, safe to add as a CI step |
| [`toolcheck.py`](toolcheck.py) | **Local toolchain inspector.** Reports which optional media/AI binaries are present (`ffmpeg`, `ffprobe`, `piper`, `whisper`, `magick`, `yt-dlp`) and their versions. Run this first when a media test fails |
| [`mcp_healthcheck.py`](mcp_healthcheck.py) | Health-check the MCP server and validate its tool-schema contract |
| [`live_tools_test.py`](live_tools_test.py) | Live end-to-end exercise of the `/tools` agent API against a running server |

## Benchmarks and media inspection

| Script | Purpose |
| :--- | :--- |
| [`benchmark.py`](benchmark.py) | Benchmark backend operations |
| [`benchmark_editing_suite.py`](benchmark_editing_suite.py) | Throughput and latency for timeline cut/trim, scene fitting, beat sync and audio operations |
| [`inspect_video.py`](inspect_video.py) | Dump the properties of a video file (codec, resolution, duration, frame rate) |
| [`test_30min_endurance_render.py`](test_30min_endurance_render.py) | 30-minute (1800 s) endurance render to surface long-run memory and temp-file problems |

## QA drivers (real media, live server)

These build actual videos and assert on the results. They are slow, they write to `storage/uploads/`, and they need `ffmpeg`.

| Script | Purpose |
| :--- | :--- |
| [`build_recook_masterpiece.py`](build_recook_masterpiece.py) | Full end-to-end re-cook of a 2 m 15 s reference clip |
| [`qa_recook_5_videos.py`](qa_recook_5_videos.py) | Build 5 source videos, transcribe each, then re-cook each |
| [`qa_ai_video_editor.py`](qa_ai_video_editor.py) | Prove the vision-driven editor actually edits a video |
| [`qa_war_full_flow.py`](qa_war_full_flow.py) | Full-flow driver: script creation → self-edit → real video render |
| [`qa_war_projects.ps1`](qa_war_projects.ps1) | Windows driver that seeds and runs the war-project scenarios |
| [`collect_nle_ui_survey.py`](collect_nle_ui_survey.py) | Collect the NLE UI survey data used by the design review (`picture/README_UI_SURVEY.md`) |

---

## Running the smoke test

Run it before a pull request or when concluding a major feature:

```powershell
# Windows PowerShell — spawns its own server
.\scripts\smoke.ps1

# Force offline document search so the run is fast and hermetic
$env:CONTENT_FACTORY_DOCUMENTS_WEB_ENABLED="false"
python scripts/smoke.py --port 8016
```

```bash
# Linux / macOS / WSL
./scripts/smoke.sh
```

A successful run ends with:

```text
SMOKE TEST PASSED — <N> checks
```

> The check count is counted at runtime (`CHECKS` starts at 0 and increments per assertion), so the number printed is authoritative. Older docs quote a fixed figure; trust the run.

## Checking the frontend without Node

Node.js is not installed by default on this machine, so the Next.js client cannot be type-checked or built in a fresh environment. `frontend_imports.py` closes the most damaging part of that gap — a refactor that deletes a module or renames an export — with no toolchain at all:

```bash
python scripts/frontend_imports.py
# Frontend import check: clean (97 files)
```

It cannot check types, component props, or the shape a hook returns. Those still require `npm run type-check` in `frontend/`.

## Note on `storage/uploads/`

Several scripts and tests write into `storage/uploads/<uuid>/`. `.gitignore` covers `storage/*`, so these artifacts will not be committed, but they do accumulate. Deleting the directories is always safe: the API recreates `storage/uploads` on startup (`api/app.py`).
