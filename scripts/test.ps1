# Run the pytest suite (Windows / PowerShell).
# Extra arguments are forwarded to pytest, e.g. scripts\test.ps1 tests\test_api.py
param([Parameter(ValueFromRemainingArguments = $true)]$PytestArgs)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Push-Location $Root
try {
    if (-not (Test-Path ".venv\Scripts\python.exe")) {
        & "$PSScriptRoot\setup.ps1"
    }
    & ".\.venv\Scripts\python.exe" -m pytest @PytestArgs
} finally {
    Pop-Location
}