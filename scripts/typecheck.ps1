# Run mypy only (Windows / PowerShell).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Push-Location $Root
try {
    & ".\.venv\Scripts\python.exe" -m mypy src
} finally {
    Pop-Location
}