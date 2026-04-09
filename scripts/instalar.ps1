Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "Instalando dependencias backend..."
python -m pip install -r "backend/requirements.txt"

Write-Host "Instalando dependencias frontend..."
Set-Location "frontend"
npm install
Set-Location ".."

Write-Host "Instalacion completada."
