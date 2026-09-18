#!/usr/bin/env bash
# Setup the development environment (Linux / macOS / WSL).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
"./.venv/bin/python" -m pip install --upgrade pip
"./.venv/bin/python" -m pip install -e ".[dev]"
echo "Setup complete. Activate with: source .venv/bin/activate"