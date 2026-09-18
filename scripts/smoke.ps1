# Run the end-to-end smoke test (Windows / PowerShell).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Push-Location $Root
try {
    & ".\.venv\Scripts\python.exe" "$PSScriptRoot\smoke.py"
} finally {
    Pop-Location
}