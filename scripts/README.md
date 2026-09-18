# Operational Scripts & Tooling: `scripts/`

This directory provides maintenance, verification, benchmarking, and development utilities for the **AI Content Factory**.

---

## Scripts Directory Catalog

| Script | Purpose & Usage |
| :--- | :--- |
| [`smoke.py`](file:///c:/Users/ADMIN/OneDrive/M%C3%A1y%20t%C3%ADnh/GitHub/ai-content-factory/scripts/smoke.py) | **End-to-End Pipeline Smoke Test**: Exercises the full lifecycle (`draft` -> `script_review` -> `script_approved` -> `generating` -> `video_review` -> `video_approved` -> `published`) against a live or spawned HTTP server on port 8080 (64 checks). |
| [`smoke.ps1`](file:///c:/Users/ADMIN/OneDrive/M%C3%A1y%20t%C3%ADnh/GitHub/ai-content-factory/scripts/smoke.ps1) | PowerShell wrapper to run `smoke.py` cleanly on Windows. |
| [`smoke.sh`](file:///c:/Users/ADMIN/OneDrive/M%C3%A1y%20t%C3%ADnh/GitHub/ai-content-factory/scripts/smoke.sh) | Shell wrapper to run `smoke.py` on Linux/macOS/WSL. |
| [`toolcheck.py`](file:///c:/Users/ADMIN/OneDrive/M%C3%A1y%20t%C3%ADnh/GitHub/ai-content-factory/scripts/toolcheck.py) | **Local Toolchain Inspector**: Checks availability and version of optional media and AI binaries (`ffmpeg`, `ffprobe`, `piper`, `whisper`, `magick`, `yt-dlp`). |
| [`benchmark_editing_suite.py`](file:///c:/Users/ADMIN/OneDrive/M%C3%A1y%20t%C3%ADnh/GitHub/ai-content-factory/scripts/benchmark_editing_suite.py) | Measures throughput and execution latency for timeline cut/trim operations, scene fitting, beat synchronization, and audio operations. |
| [`dev.ps1`](file:///c:/Users/ADMIN/OneDrive/M%C3%A1y%20t%C3%ADnh/GitHub/ai-content-factory/scripts/dev.ps1) / [`dev.sh`](file:///c:/Users/ADMIN/OneDrive/M%C3%A1y%20t%C3%ADnh/GitHub/ai-content-factory/scripts/dev.sh) | Development server launcher running Uvicorn with live hot-reloading enabled. |

---

## Running the Smoke Test

Before submitting pull requests or concluding major features, execute the smoke test:

```powershell
# Windows PowerShell
.\scripts\smoke.ps1

# Or with offline web search forced (guarantees fast local hermetic execution)
$env:CONTENT_FACTORY_DOCUMENTS_WEB_ENABLED="false"
python scripts/smoke.py
```

```bash
# Linux / macOS / WSL
./scripts/smoke.sh
```

A successful smoke test will conclude with:
```text
SMOKE TEST PASSED — 64 checks
```
