---
name: lint
description: >-
  Lint and type-check the codebase with ruff (check + format) and mypy,
  using the same gates as GitHub Actions. Use after editing Python code or
  when the user asks to lint / format / typecheck / quality-gate the repo.
---

# Lint & type-check

1. Run the wrapper:
   - Windows: `scripts/lint.ps1`
   - Linux/macOS/WSL: `scripts/lint.sh`
2. This runs, in order:
   - `python -m ruff check src tests`
   - `python -m ruff format --check src tests`
   - `python -m mypy src`
3. Fix every issue until the script exits 0:
   - ruff `E/F/I/UP/B` rule violations → fix code or imports.
   - format drift → run `python -m ruff format src tests` then re-check.
   - mypy errors → add/annotate types; do not silence with `# type: ignore`
     unless there is a strong reason.
4. For a mypy-only pass use `scripts/typecheck.ps1` / `scripts/typecheck.sh`.