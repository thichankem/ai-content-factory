# Start the development server (Windows / PowerShell).
param([int]$Port = 8080)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Push-Location $Root
try {
    if (-not (Test-Path ".venv\Scripts\python.exe")) {
        & "$PSScriptRoot\setup.ps1"
    }
    & ".\.venv\Scripts\python.exe" -m uvicorn content_factory.api:app --app-dir src --reload --port $Port
} finally {
    Pop-Location
}