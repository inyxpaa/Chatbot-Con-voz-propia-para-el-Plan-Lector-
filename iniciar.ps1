Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   INICIANDO CHATBOT PLAN LECTOR" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Refrescar PATH de la sesión actual
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

# $PSScriptRoot captura la carpeta real donde está el script, sea cual sea el PC
$ProjectRoot = $PSScriptRoot

# 1. Instalar/Verificar dependencias backend
Write-Host "`n[1/4] Comprobando dependencias del Backend (Python)..." -ForegroundColor Yellow
$BackendReqs = Join-Path $ProjectRoot "backend\requirements.txt"

$pythonPath = ""
if (Get-Command py -ErrorAction SilentlyContinue) {
    $pythonPath = "py"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $pyTest = $null
    try {
        $pyTest = & python --version 2>&1
    } catch {
        $pyTest = $_.Exception.Message
    }
    if (-not (($pyTest -as [string]) -match "no se encontr" -or ($pyTest -as [string]) -match "was not found")) {
        $pythonPath = "python"
    }
}

if ($pythonPath -eq "") {
    Write-Host "ERROR: Python no está instalado en este PC. Por favor, instala Python y añádelo al PATH." -ForegroundColor Red
    Read-Host "Presiona Enter para salir..."
    exit
} else {
    Write-Host "Python detectado. Verificando librerias requeridas..." -ForegroundColor Green
    & $pythonPath -m pip install -r $BackendReqs
}

# 2. Instalar dependencias Frontend
Write-Host "`n[2/4] Comprobando dependencias del Frontend (React/Node.js)..." -ForegroundColor Yellow
$FrontendPath = Join-Path $ProjectRoot "frontend"

if (Get-Command npm -ErrorAction SilentlyContinue) {
    Write-Host "Node detectado. Instalando/Verificando paquetes de React..." -ForegroundColor Green
    Set-Location $FrontendPath
    npm install
    Set-Location $ProjectRoot
} else {
    Write-Host "ERROR: Node.js no está instalado en este PC." -ForegroundColor Red
    Read-Host "Presiona Enter para salir..."
    exit
}

# 3. Limpiar puertos en uso
Write-Host "`n[3/4] Cierre de procesos antiguos en los puertos 8000 y 5173..." -ForegroundColor Yellow
foreach ($port in @(8000, 5173)) {
    $procesos = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess | Select-Object -Unique
    foreach ($p in $procesos) {
        Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
        Write-Host "  -> Detenido proceso $p usando el puerto $port" -ForegroundColor Cyan
    }
}

# 4. Lanzar Backend
Write-Host "`n[4/4] Lanzando Backend de FastAPI y Frontend de React..." -ForegroundColor Yellow
$BackendCmd = "$pythonPath -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload"
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", "cd `"$ProjectRoot`"; $BackendCmd"

# Lanzar Frontend
$FrontendCmd = "npm run dev -- --port 5173 --strictPort"
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", "cd `"$FrontendPath`"; $FrontendCmd"

Write-Host "`n!Todo listo! Se han abierto dos ventanas con el servidor." -ForegroundColor Green
Write-Host "Puedes cerrar esta." -ForegroundColor Cyan
Start-Sleep -Seconds 5
