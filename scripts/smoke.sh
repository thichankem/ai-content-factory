#!/usr/bin/env bash
# Run the end-to-end smoke test (Linux / macOS / WSL).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
exec "./.venv/bin/python" scripts/smoke.py