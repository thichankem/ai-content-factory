#!/usr/bin/env bash
# Start the development server (Linux / macOS / WSL).
# Usage: scripts/dev.sh [PORT]
set -euo pipefail
PORT="${1:-8080}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if [ ! -x ".venv/bin/python" ]; then
  ./scripts/setup.sh
fi
exec "./.venv/bin/python" -m uvicorn content_factory.api:app --app-dir src --reload --port "$PORT"