# Run the ruff + mypy quality gates (Windows / PowerShell).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Push-Location $Root
try {
    if (-not (Test-Path ".venv\Scripts\python.exe")) {
        & "$PSScriptRoot\setup.ps1"
    }
    & ".\.venv\Scripts\python.exe" -m ruff check src tests
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & ".\.venv\Scripts\python.exe" -m ruff format --check src tests
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & ".\.venv\Scripts\python.exe" -m mypy src
} finally {
    Pop-Location
}