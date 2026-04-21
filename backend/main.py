# --- Chatbot Plan Lector v2.2 (RAG + modelo local AWS + Postgres + Admin Panel) ---
import os
import csv
import io
import json
import time
import logging
import hashlib
import re
import asyncio
import datetime
from functools import lru_cache
from pathlib import Path

import httpx
from fastapi import FastAPI, Depends, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from database import SessionLocal, create_tables, Busqueda, User
from rag_engine import retrieve_context, build_rag_prompt, warmup
from modelo.filtro import verificar_consulta

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("chatbot")

# ---------------------------------------------------------------------------
# Configuración — Modelo
# ---------------------------------------------------------------------------
#
#   MODEL_PROVIDER   → "local" | "tgi" | "openai" | "ollama" | "hf"
#   LOCAL_MODEL_PATH → ruta al modelo fine-tuneado en disco (provider=local)
#   MODEL_API_URL    → URL del servidor (tgi/openai/ollama)
#   MODEL_NAME       → nombre del modelo en el servidor
#   HF_TOKEN         → token HF (solo provider=hf)
#   MAX_NEW_TOKENS   → tokens a generar (default: 256)
#   MODEL_TIMEOUT_S  → timeout llamada HTTP al modelo (default: 60)

GOOGLE_CLIENT_ID = "22015513342-rp17v8jccio7gvnhkdma2vpigerrnu44.apps.googleusercontent.com"

HF_MODEL_ID    = "inyxpa/chatbot"
HF_TOKEN       = os.getenv("HF_TOKEN", "")
HF_API_URL     = f"https://api-inference.huggingface.co/models/{HF_MODEL_ID}"

MODEL_PROVIDER  = os.getenv("MODEL_PROVIDER", "local").lower()
MODEL_API_URL   = os.getenv("MODEL_API_URL", HF_API_URL)
MODEL_NAME      = os.getenv("MODEL_NAME", HF_MODEL_ID)
MAX_NEW_TOKENS  = int(os.getenv("MAX_NEW_TOKENS", "256"))
MODEL_TIMEOUT_S = int(os.getenv("MODEL_TIMEOUT_S", "60"))

_default_model_path = (
    Path(__file__).parent / "modelo" / "entrenamiento" / "output" / "qwen_finetuned"
)
LOCAL_MODEL_PATH = Path(os.getenv("LOCAL_MODEL_PATH", str(_default_model_path)))

SYSTEM_PROMPT = (
    "Eres un asistente del Plan Lector del IES Comercio. "
    "Ayudas a los alumnos con dudas sobre los libros y lecturas del Plan Lector. "
    "Responde siempre en español, de forma clara y concisa."
)

# ---------------------------------------------------------------------------
# Configuración — Administradores
# ---------------------------------------------------------------------------
#
#   ADMIN_EMAILS → lista de emails separados por coma (soporta ñ y cualquier
#                  carácter UTF-8, ej: nuñez@ies.com,gsoriano@iescomercio.com)
#
# Python lee variables de entorno como strings Unicode nativos, así que
# cualquier carácter UTF-8 (ñ, tildes, etc.) funciona sin configuración extra.
# En Linux/AWS los env vars son UTF-8 por defecto.

_admin_emails_raw = os.getenv(
    "ADMIN_EMAILS",
    "gsoriano@iescomercio.com,test@example.com"
)
ADMIN_EMAILS: set[str] = {
    e.strip().lower()
    for e in _admin_emails_raw.split(",")
    if e.strip()
}
logger.info(f"[ADMIN] Administradores configurados: {len(ADMIN_EMAILS)} email(s)")


def check_admin(id_info: dict) -> None:
    """Verifica que el usuario autenticado sea administrador. Lanza 403 si no."""
    email = id_info.get("email", "").lower()
    if email not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="No tienes permisos de administrador")


# ---------------------------------------------------------------------------
# Modelo local — singleton cargado una vez al arrancar
# ---------------------------------------------------------------------------

_local_pipeline = None


def load_local_model():
    """Carga el modelo Qwen2.5-QLoRA desde disco una sola vez al arrancar."""
    global _local_pipeline
    if MODEL_PROVIDER != "local":
        return
    try:
        import torch
        from transformers import pipeline as hf_pipeline

        if not LOCAL_MODEL_PATH.exists():
            logger.warning(
                f"[MODELO] Ruta no encontrada: {LOCAL_MODEL_PATH}. "
                "Fallback: se usará HF cloud si se configura MODEL_PROVIDER=hf."
            )
            return

        device = 0 if torch.cuda.is_available() else -1
        logger.info(f"[MODELO] Cargando modelo desde {LOCAL_MODEL_PATH} (device={device})...")
        _local_pipeline = hf_pipeline(
            "text-generation",
            model=str(LOCAL_MODEL_PATH),
            device=device,
            torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
        )
        logger.info("[MODELO] Modelo cargado correctamente en memoria.")
    except Exception as e:
        logger.error(f"[MODELO] Error al cargar el modelo local: {e}")
        _local_pipeline = None


# ---------------------------------------------------------------------------
# Inicialización
# ---------------------------------------------------------------------------

create_tables()
warmup()            # Precarga ChromaDB → elimina latencia del primer request
load_local_model()  # Carga el modelo fine-tuneado en memoria

app = FastAPI(
    title="Chatbot 'Con voz propia' — Plan Lector",
    version="2.2.0",
    description="API del chatbot RAG para el Plan Lector del IES Comercio",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Privacidad — Tarea 1
# ---------------------------------------------------------------------------

def hash_email(email: str) -> str:
    if not email:
        return "anonymous"
    return hashlib.sha256(email.lower().strip().encode()).hexdigest()


def scrub_pii(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', '[EMAIL]', text)
    text = re.sub(r'\+?\d{2,4}[-.\s]?\d{3,4}[-.\s]?\d{3,4}[-.\s]?\d{0,4}', '[TELÉFONO]', text)
    return text


# ---------------------------------------------------------------------------
# Modelos Pydantic
# ---------------------------------------------------------------------------

class ChatQuery(BaseModel):
    mensaje:    str
    session_id: str | None = None


class ChatResponse(BaseModel):
    respuesta: str
    fuentes:   list[str]


class BusquedaOut(BaseModel):
    id:                  int
    user_email:          str | None
    session_id:          str | None
    pregunta:            str
    respuesta:           str | None
    fuentes:             str | None
    bloqueada:           bool
    categoria_bloqueo:   str | None
    tiempo_respuesta_ms: float | None
    creada_en:           str | None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# DB
# ---------------------------------------------------------------------------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Autenticación Google
# ---------------------------------------------------------------------------

def verify_google_token(authorization: str = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No se proporcionó token de sesión")
    token = authorization.split(" ")[1]
    if token == "token-de-prueba":
        return {"email": "test@example.com", "name": "Test User", "picture": ""}
    try:
        idinfo = id_token.verify_oauth2_token(
            token, google_requests.Request(), GOOGLE_CLIENT_ID
        )
        return idinfo
    except Exception as e:
        logger.warning(f"Token inválido: {e}")
        raise HTTPException(status_code=401, detail="Token de Google inválido")


# ---------------------------------------------------------------------------
# Inferencia — multi-proveedor async
# ---------------------------------------------------------------------------

async def query_model_async(prompt: str) -> str:
    # ── LOCAL: modelo fine-tuneado en disco ─────────────────────────────────
    if MODEL_PROVIDER == "local":
        if _local_pipeline is None:
            logger.error("[MODELO] Pipeline local no disponible.")
            return "El modelo no está disponible en este momento. Contacta al administrador."
        full_prompt = (
            f"<|im_start|>system\n{SYSTEM_PROMPT}<|im_end|>\n"
            f"<|im_start|>user\n{prompt}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )
        try:
            result = await asyncio.to_thread(
                _local_pipeline,
                full_prompt,
                max_new_tokens=MAX_NEW_TOKENS,
                temperature=0.7,
                do_sample=True,
                return_full_text=False,
            )
            text = result[0]["generated_text"].strip()
            text = text.replace("<|im_end|>", "").strip()
            return text or "No pude generar una respuesta."
        except Exception as e:
            logger.error(f"[MODELO] Error en inferencia local: {e}")
            return "Hubo un error al generar la respuesta. Inténtalo de nuevo."

    headers: dict = {}
    url:     str  = ""
    payload: dict = {}

    # ── HF Inference API / TGI local ────────────────────────────────────────
    if MODEL_PROVIDER in ("hf", "tgi"):
        if HF_TOKEN:
            headers["Authorization"] = f"Bearer {HF_TOKEN}"
        full_prompt = (
            f"<|im_start|>system\n{SYSTEM_PROMPT}<|im_end|>\n"
            f"<|im_start|>user\n{prompt}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )
        payload = {
            "inputs": full_prompt,
            "parameters": {
                "max_new_tokens": MAX_NEW_TOKENS,
                "temperature": 0.7,
                "do_sample": True,
                "return_full_text": False,
            },
        }
        url = MODEL_API_URL

    elif MODEL_PROVIDER == "openai":
        if HF_TOKEN:
            headers["Authorization"] = f"Bearer {HF_TOKEN}"
        headers["Content-Type"] = "application/json"
        payload = {
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            "max_tokens": MAX_NEW_TOKENS,
            "temperature": 0.7,
        }
        url = f"{MODEL_API_URL.rstrip('/')}/v1/chat/completions"

    elif MODEL_PROVIDER == "ollama":
        payload = {
            "model":  MODEL_NAME,
            "prompt": f"{SYSTEM_PROMPT}\n\n{prompt}",
            "stream": False,
            "options": {"num_predict": MAX_NEW_TOKENS, "temperature": 0.7},
        }
        url = f"{MODEL_API_URL.rstrip('/')}/api/generate"

    else:
        logger.error(f"MODEL_PROVIDER desconocido: '{MODEL_PROVIDER}'")
        return "Error de configuración: MODEL_PROVIDER no válido."

    try:
        async with httpx.AsyncClient(timeout=MODEL_TIMEOUT_S) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            res_json = response.json()

        if MODEL_PROVIDER in ("hf", "tgi"):
            if isinstance(res_json, list) and res_json:
                text = res_json[0].get("generated_text", "")
                if "<|im_start|>assistant" in text:
                    text = text.split("<|im_start|>assistant")[-1]
                    text = text.replace("<|im_end|>", "").strip()
                return text.strip() or "No pude generar una respuesta."
            if isinstance(res_json, dict):
                return res_json.get("generated_text", "No pude generar una respuesta.").strip()

        elif MODEL_PROVIDER == "openai":
            choices = res_json.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "").strip()

        elif MODEL_PROVIDER == "ollama":
            return res_json.get("response", "").strip()

        return "No pude obtener una respuesta del modelo."

    except httpx.TimeoutException:
        logger.error(f"Timeout ({MODEL_TIMEOUT_S}s) esperando al modelo en {url}")
        return "El asistente tardó demasiado en responder. Inténtalo de nuevo en unos segundos."
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP {e.response.status_code} del modelo: {e.response.text[:300]}")
        return "Hubo un error al conectar con el cerebro del asistente."
    except Exception as e:
        logger.error(f"Error inesperado en query_model_async: {e}")
        return "Hubo un error al conectar con el cerebro del asistente."


# ===========================================================================
# ENDPOINTS PÚBLICOS
# ===========================================================================

@app.get("/health")
async def health():
    """Health-check para load balancers y monitorización de AWS."""
    return {
        "status":         "ok",
        "version":        "2.2.0",
        "model_provider": MODEL_PROVIDER,
        "model_url":      MODEL_API_URL,
    }


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    query:   ChatQuery,
    db:      Session = Depends(get_db),
    id_info: dict    = Depends(verify_google_token),
) -> ChatResponse:
    """Flujo completo: filtro → RAG → inferencia → log anonimizado."""
    inicio_total = time.perf_counter()
    pregunta     = query.mensaje.strip()
    user_email   = id_info["email"]

    if not pregunta:
        return ChatResponse(respuesta="Escribe una consulta para poder ayudarte.", fuentes=[])

    # 1. Filtro de contenido
    resultado_filtro = verificar_consulta(pregunta)
    if not resultado_filtro["aceptado"]:
        try:
            db.add(Busqueda(
                user_email=hash_email(user_email),
                session_id=query.session_id,
                pregunta=scrub_pii(pregunta),
                respuesta=resultado_filtro["mensaje"],
                fuentes=json.dumps([]),
                bloqueada=True,
                categoria_bloqueo=resultado_filtro.get("categoria"),
                tiempo_respuesta_ms=0.0,
            ))
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Error registrando consulta bloqueada: {e}")
        return ChatResponse(respuesta=resultado_filtro["mensaje"], fuentes=[])

    # 2. RAG
    t_rag = time.perf_counter()
    contexto, fuentes_rag = await asyncio.to_thread(retrieve_context, pregunta)
    t_rag_ms = (time.perf_counter() - t_rag) * 1000
    logger.info(f"[RAG] {len(fuentes_rag)} fragmentos en {t_rag_ms:.1f}ms")

    # 3. Prompt
    prompt = build_rag_prompt(pregunta, contexto)

    # 4. Usuario en BD
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        db.add(User(email=user_email, name=id_info.get("name"), picture=id_info.get("picture")))
        try:
            db.commit()
        except Exception:
            db.rollback()

    # 5. Inferencia
    t_modelo = time.perf_counter()
    respuesta = await query_model_async(prompt)
    t_modelo_ms = (time.perf_counter() - t_modelo) * 1000
    logger.info(f"[MODELO] Respuesta en {t_modelo_ms:.1f}ms")

    fuentes = fuentes_rag + [f"modelo:{MODEL_PROVIDER}"]
    tiempo_total_ms = (time.perf_counter() - inicio_total) * 1000
    logger.info(f"[TOTAL] {tiempo_total_ms:.1f}ms (RAG={t_rag_ms:.0f}ms + modelo={t_modelo_ms:.0f}ms)")

    # 6. Log anonimizado
    try:
        db.add(Busqueda(
            user_email=hash_email(user_email),
            session_id=query.session_id,
            pregunta=scrub_pii(pregunta),
            respuesta=scrub_pii(respuesta),
            fuentes=json.dumps(fuentes),
            bloqueada=False,
            tiempo_respuesta_ms=tiempo_total_ms,
        ))
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"FATAL: Error al guardar en Postgres: {e}")

    return ChatResponse(respuesta=respuesta, fuentes=fuentes)


# ===========================================================================
# ENDPOINTS DE ADMINISTRACIÓN — Tarea 3
# ===========================================================================

@app.get("/admin/stats")
async def admin_stats(
    db:      Session = Depends(get_db),
    id_info: dict    = Depends(verify_google_token),
):
    """KPIs del sistema: totales, latencia media y consultas por día (7 días)."""
    check_admin(id_info)

    total      = db.query(Busqueda).count()
    bloqueadas = db.query(Busqueda).filter(Busqueda.bloqueada == True).count()
    usuarios   = db.query(Busqueda.user_email).distinct().count()
    avg_ms     = db.query(func.avg(Busqueda.tiempo_respuesta_ms)).filter(
        Busqueda.bloqueada == False,
        Busqueda.tiempo_respuesta_ms.isnot(None),
    ).scalar() or 0.0

    # Consultas por día en Python (compatible SQLite dev + PostgreSQL AWS)
    hoy  = datetime.datetime.utcnow().date()
    dias = [(hoy - datetime.timedelta(days=i)) for i in range(6, -1, -1)]

    recientes = db.query(Busqueda).filter(
        Busqueda.creada_en >= datetime.datetime.utcnow() - datetime.timedelta(days=7)
    ).all()

    conteo = {d: 0 for d in dias}
    for r in recientes:
        if r.creada_en:
            dia = r.creada_en.date()
            if dia in conteo:
                conteo[dia] += 1

    consultas_por_dia = [
        {"fecha": str(d), "etiqueta": d.strftime("%d/%m"), "total": conteo[d]}
        for d in dias
    ]

    return {
        "total_consultas":      total,
        "usuarios_unicos":      usuarios,
        "consultas_bloqueadas": bloqueadas,
        "tasa_bloqueo_pct":     round(bloqueadas / total * 100, 1) if total > 0 else 0.0,
        "latencia_media_ms":    round(avg_ms),
        "consultas_por_dia":    consultas_por_dia,
    }


@app.get("/admin/history")
async def admin_history(
    db:             Session = Depends(get_db),
    id_info:        dict    = Depends(verify_google_token),
    page:           int     = Query(1, ge=1),
    limit:          int     = Query(50, ge=1, le=200),
    search:         str     = Query(""),
    solo_bloqueadas: bool   = Query(False),
):
    """Historial paginado con búsqueda en pregunta/respuesta y filtro de bloqueadas."""
    check_admin(id_info)

    q = db.query(Busqueda)
    if search:
        patron = f"%{search}%"
        q = q.filter(
            Busqueda.pregunta.ilike(patron) | Busqueda.respuesta.ilike(patron)
        )
    if solo_bloqueadas:
        q = q.filter(Busqueda.bloqueada == True)

    total    = q.count()
    offset   = (page - 1) * limit
    registros = q.order_by(Busqueda.creada_en.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "page":  page,
        "pages": max(1, (total + limit - 1) // limit),
        "data": [
            BusquedaOut(
                id=r.id,
                user_email=r.user_email,
                session_id=r.session_id,
                pregunta=r.pregunta,
                respuesta=r.respuesta,
                fuentes=r.fuentes,
                bloqueada=bool(r.bloqueada),
                categoria_bloqueo=r.categoria_bloqueo,
                tiempo_respuesta_ms=r.tiempo_respuesta_ms,
                creada_en=r.creada_en.isoformat() if r.creada_en else None,
            )
            for r in registros
        ],
    }


@app.get("/admin/health")
async def admin_health_detail(
    db:      Session = Depends(get_db),
    id_info: dict    = Depends(verify_google_token),
):
    """Estado detallado del sistema: modelo, ChromaDB y Postgres."""
    check_admin(id_info)

    # Postgres
    try:
        total_registros = db.query(Busqueda).count()
        postgres_ok     = True
    except Exception:
        total_registros = 0
        postgres_ok     = False

    # ChromaDB — acceso al singleton ya existente
    from rag_engine import _get_collection, CHROMA_DB_PATH, COLLECTION_NAME
    collection     = _get_collection()
    chroma_ok      = collection is not None
    chroma_chunks  = collection.count() if collection else 0

    # Modelo
    modelo_cargado = _local_pipeline is not None

    return {
        "modelo": {
            "cargado":   modelo_cargado,
            "provider":  MODEL_PROVIDER,
            "ruta":      str(LOCAL_MODEL_PATH) if MODEL_PROVIDER == "local" else MODEL_API_URL,
        },
        "chromadb": {
            "ok":        chroma_ok,
            "chunks":    chroma_chunks,
            "coleccion": COLLECTION_NAME,
            "ruta":      str(CHROMA_DB_PATH),
        },
        "postgres": {
            "ok":              postgres_ok,
            "total_registros": total_registros,
        },
    }


@app.get("/admin/users")
async def admin_users(
    db:      Session = Depends(get_db),
    id_info: dict    = Depends(verify_google_token),
):
    """Lista de usuarios únicos con total de consultas y último acceso."""
    check_admin(id_info)

    resultado = (
        db.query(
            Busqueda.user_email,
            func.count(Busqueda.id).label("total_consultas"),
            func.max(Busqueda.creada_en).label("ultimo_acceso"),
        )
        .group_by(Busqueda.user_email)
        .order_by(func.count(Busqueda.id).desc())
        .all()
    )

    return [
        {
            "user_email":      r.user_email,
            "total_consultas": r.total_consultas,
            "ultimo_acceso":   r.ultimo_acceso.isoformat() if r.ultimo_acceso else None,
        }
        for r in resultado
    ]


@app.get("/admin/export")
async def admin_export(
    db:      Session = Depends(get_db),
    id_info: dict    = Depends(verify_google_token),
):
    """Exporta el historial completo (máx. 5000 registros) como CSV descargable."""
    check_admin(id_info)

    registros = (
        db.query(Busqueda)
        .order_by(Busqueda.creada_en.desc())
        .limit(5000)
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "fecha", "usuario_hash", "pregunta", "respuesta",
        "bloqueada", "categoria_bloqueo", "tiempo_ms",
    ])
    for r in registros:
        writer.writerow([
            r.id,
            r.creada_en.isoformat() if r.creada_en else "",
            r.user_email or "",
            r.pregunta or "",
            r.respuesta or "",
            "sí" if r.bloqueada else "no",
            r.categoria_bloqueo or "",
            round(r.tiempo_respuesta_ms or 0),
        ])

    output.seek(0)
    # Incluir BOM UTF-8 para que Excel abra tildes y ñ correctamente
    contenido = "\ufeff" + output.getvalue()

    return StreamingResponse(
        iter([contenido]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=historial_chatbot.csv"},
    )