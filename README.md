# Chatbot "Con voz propia" - Plan Lector

Proyecto con frontend (React/Vite) y backend (FastAPI + ChromaDB) para consultas tipo chatbot.

## Estructura

- `frontend/`: interfaz web.
- `backend/`: API y persistencia local.
- `backend/datalake/`: datos y artefactos de recuperación.
- `backend/scripts/`: scripts de instalación y arranque.

## Inicio rápido (Windows / PowerShell)

Desde la raíz del repo:

```powershell
.\backend\scripts\instalar.ps1
.\backend\scripts\lanzar-todo.ps1
```

Esto abre dos ventanas:
- Backend en `http://127.0.0.1:8000`
- Frontend en `http://localhost:5173`

## Arranque por separado

```powershell
.\backend\scripts\lanzar-backend.ps1
.\backend\scripts\lanzar-frontend.ps1
```

## Swagger de la API

- `http://127.0.0.1:8000/docs`
