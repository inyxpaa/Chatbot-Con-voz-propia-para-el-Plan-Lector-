Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "Abriendo backend y frontend en dos ventanas..."

Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "scripts/lanzar-backend.ps1"
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "scripts/lanzar-frontend.ps1"

Write-Host "Listo."
