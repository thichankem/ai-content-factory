---
name: run-dev
description: >-
  Start the AI Content Factory development server (FastAPI + vanilla-JS
  frontend in one process) at http://127.0.0.1:8080. Use when the user asks
  to run/start the app, open the UI, test the API, or bootstrap the dev
  environment.
---

# Run the dev server

1. Ensure the environment is installed:
   - Windows: `scripts/setup.ps1`
   - Linux/macOS/WSL: `scripts/setup.sh`
2. Start the server in the foreground so the user sees logs:
   - Windows: `scripts/dev.ps1`
   - Linux/macOS/WSL: `scripts/dev.sh`
   - Optional port argument: `scripts/dev.sh 9090`
3. Verify with a quick health check:
   `curl -s http://127.0.0.1:8080/health` → expect `{"status":"ok", ...}`
4. Tell the user the two URLs: UI at `/`, Swagger docs at `/docs`.

If the server is already running on the port, do NOT start a second one —
reuse it and only report the health check result.