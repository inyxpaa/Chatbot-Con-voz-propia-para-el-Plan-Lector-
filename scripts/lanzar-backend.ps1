Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "Lanzando backend en http://127.0.0.1:8000 ..."
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
