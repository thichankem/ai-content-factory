#!/usr/bin/env bash
# Run mypy only (Linux / macOS / WSL).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
exec "./.venv/bin/python" -m mypy src