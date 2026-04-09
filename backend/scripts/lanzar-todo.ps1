Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "Abriendo backend y frontend en dos ventanas..."

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Start-Process powershell -WorkingDirectory $repoRoot -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "backend/scripts/lanzar-backend.ps1"
Start-Process powershell -WorkingDirectory $repoRoot -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "backend/scripts/lanzar-frontend.ps1"

Write-Host "Listo."
