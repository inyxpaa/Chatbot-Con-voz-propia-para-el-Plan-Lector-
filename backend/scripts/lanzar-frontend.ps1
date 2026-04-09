Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Set-Location "frontend"
Write-Host "Lanzando frontend en http://localhost:5173 ..."
npm run dev -- --port 5173 --strictPort
