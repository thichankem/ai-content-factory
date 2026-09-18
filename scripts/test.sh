#!/usr/bin/env bash
# Run the pytest suite (Linux / macOS / WSL).
# Extra arguments are forwarded to pytest, e.g. scripts/test.sh tests/test_api.py
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
exec "./.venv/bin/python" -m pytest "$@"