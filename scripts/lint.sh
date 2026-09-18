#!/usr/bin/env bash
# Run the ruff + mypy quality gates (Linux / macOS / WSL).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
"./.venv/bin/python" -m ruff check src tests
"./.venv/bin/python" -m ruff format --check src tests
"./.venv/bin/python" -m mypy src