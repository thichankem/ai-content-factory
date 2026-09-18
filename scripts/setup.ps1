# Setup the development environment (Windows / PowerShell).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Push-Location $Root
try {
    if (-not (Test-Path ".venv")) {
        python -m venv .venv
    }
    & ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
    & ".\.venv\Scripts\python.exe" -m pip install -e ".[dev]"
    Write-Host "Setup complete. Activate with: .\.venv\Scripts\Activate.ps1"
} finally {
    Pop-Location
}