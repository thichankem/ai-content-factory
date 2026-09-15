---
name: test
description: >-
  Run the pytest suite for ai-content-factory. Use whenever code is changed
  before reporting a task as done, or when the user asks to run tests.
---

# Run the test suite

> **Note:** The test suite and helper scripts are planned but not yet
> implemented. These steps define the target workflow.

1. Use the wrapper script (it activates the virtual environment):
   - Windows: `scripts/test.ps1`
   - Linux/macOS/WSL: `scripts/test.sh`
2. Pass pytest arguments through when needed, e.g.
   - single file: `scripts/test.sh tests/test_domain.py`
   - with coverage: `scripts/test.sh --cov=content_factory --cov-report=term-missing`
3. Report pass/fail counts to the user. Fix failures before finishing the task.

Expected baseline: the full suite (~25 tests) passes in a few seconds.