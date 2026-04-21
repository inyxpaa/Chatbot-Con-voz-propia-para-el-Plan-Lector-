# --- Chatbot Plan Lector v2.1 (RAG + modelo local AWS + Postgres) ---
import os
import json
import time
import logging
import hashlib
import re
import asyncio
from functools import lru_cache
from pathlib import Path

import httpx
from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
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
# Configuración del modelo
# ---------------------------------------------------------------------------
#
# Variables de entorno esperadas en AWS (.env o systemd unit):
#
#   MODEL_PROVIDER   → tipo de servidor del modelo local
#                      "tgi"    : Text Generation Inference (HF, mismo API)
#                      "openai" : vLLM, LM Studio, llama.cpp (OpenAI-compat)
#                      "ollama" : Ollama
#                      "hf"     : HF Inference API cloud (fallback dev)
#
#   MODEL_API_URL    → URL base del servidor del modelo
#                      Ejemplos: http://localhost:8080
#                                http://localhost:8000
#                                http://localhost:11434
#
#   MODEL_NAME       → nombre/ruta del modelo cargado en el servidor
#                      Ejemplo: inyxpa/chatbot  o  /models/chatbot
#
#   HF_TOKEN         → token de HF (solo necesario si MODEL_PROVIDER=hf)
#   MAX_NEW_TOKENS   → max tokens a generar (default: 256)
#   MODEL_TIMEOUT_S  → timeout en segundos para la llamada al modelo (default: 60)

GOOGLE_CLIENT_ID = "22015513342-rp17v8jccio7gvnhkdma2vpigerrnu44.apps.googleusercontent.com"

HF_MODEL_ID    = "inyxpa/chatbot"
HF_TOKEN       = os.getenv("HF_TOKEN", "")
HF_API_URL     = f"https://api-inference.huggingface.co/models/{HF_MODEL_ID}"

MODEL_PROVIDER  = os.getenv("MODEL_PROVIDER", "local").lower()
MODEL_API_URL   = os.getenv("MODEL_API_URL", HF_API_URL)
MODEL_NAME      = os.getenv("MODEL_NAME", HF_MODEL_ID)
MAX_NEW_TOKENS  = int(os.getenv("MAX_NEW_TOKENS", "256"))
MODEL_TIMEOUT_S = int(os.getenv("MODEL_TIMEOUT_S", "60"))

# Ruta al modelo fine-tuneado en disco (solo para MODEL_PROVIDER=local)
# Default: backend/modelo/entrenamiento/output/qwen_finetuned
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
# Modelo local — singleton cargado una vez al arrancar
# ---------------------------------------------------------------------------

_local_pipeline = None  # HuggingFace pipeline (solo para provider=local)


def load_local_model():
    """
    Carga el modelo fine-tuneado Qwen2.5-QLoRA directamente con transformers.

    Se llama UNA vez al arrancar el servidor. El pipeline queda en memoria
    para servir todas las peticiones sin overhead de carga.

    Si el modelo no está en disco, registra un warning y el sistema
    cae en modo degradado (devuelve mensaje de error).
    """
    global _local_pipeline
    if MODEL_PROVIDER != "local":
        return

    try:
        # Importar transformers aquí: si el provider no es local, no se carga
        import torch
        from transformers import pipeline as hf_pipeline

        if not LOCAL_MODEL_PATH.exists():
            logger.warning(
                f"[MODELO] Ruta del modelo no encontrada: {LOCAL_MODEL_PATH}. "
                "Usando HF cloud como fallback."
            )
            return

        device = 0 if torch.cuda.is_available() else -1  # GPU si disponible
        logger.info(f"[MODELO] Cargando modelo desde {LOCAL_MODEL_PATH} (device={device})...")

        _local_pipeline = hf_pipeline(
            "text-generation",
            model=str(LOCAL_MODEL_PATH),
            device=device,
            torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
        )
        logger.info("[MODELO] Modelo local cargado correctamente en memoria.")

    except Exception as e:
        logger.error(f"[MODELO] Error al cargar el modelo local: {e}")
        _local_pipeline = None


# ---------------------------------------------------------------------------
# Inicialización
# ---------------------------------------------------------------------------

create_tables()
warmup()         # Precarga ChromaDB → elimina latencia del primer request
load_local_model()  # Carga el modelo fine-tuneado en memoria

app = FastAPI(
    title="Chatbot 'Con voz propia' — Plan Lector",
    version="2.1.0",
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
    """Retorna un hash SHA-256 del email para anonimización."""
    if not email:
        return "anonymous"
    return hashlib.sha256(email.lower().strip().encode()).hexdigest()


def scrub_pii(text: str) -> str:
    """Ofusca emails y números de teléfono en el texto."""
    if not text:
        return ""
    # Emails
    text = re.sub(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', '[EMAIL]', text)
    # Teléfonos — solo ASCII, sin caracteres invisibles
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
    """Schema de serialización para el historial de admin."""
    id:                  int
    user_email:          str | None
    session_id:          str | None
    pregunta:            str
    respuesta:           str | None
    fuentes:             str | None
    bloqueada:           bool
    categoria_bloqueo:   str | None
    tiempo_respuesta_ms: float | None
    creada_en:           str | None  # ISO string

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

    # Bypass para pruebas (solo desarrollo)
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
    """
    Llama al modelo LLM según MODEL_PROVIDER:
      local     → modelo fine-tuneado en disco con transformers (DEFAULT en AWS)
      hf / tgi  → HF Inference API o Text Generation Inference
      openai    → API compatible con OpenAI (vLLM, LM Studio)
      ollama    → Ollama local
    """
    # ── LOCAL: modelo fine-tuneado en disco ─────────────────────────────────
    if MODEL_PROVIDER == "local":
        if _local_pipeline is None:
            logger.error("[MODELO] Pipeline local no disponible. Verifica LOCAL_MODEL_PATH.")
            return "El modelo no está disponible en este momento. Contacta al administrador."

        # Construir el prompt en formato ChatML (Qwen2.5-Instruct)
        full_prompt = (
            f"<|im_start|>system\n{SYSTEM_PROMPT}<|im_end|>\n"
            f"<|im_start|>user\n{prompt}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )
        try:
            # asyncio.to_thread para no bloquear el event loop de FastAPI
            result = await asyncio.to_thread(
                _local_pipeline,
                full_prompt,
                max_new_tokens=MAX_NEW_TOKENS,
                temperature=0.7,
                do_sample=True,
                return_full_text=False,  # solo la parte generada por el asistente
            )
            text = result[0]["generated_text"].strip()
            # Limpiar token de fin si viene incluido
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
        # Formato ChatML — compatible con Qwen y el fine-tune del proyecto
        full_prompt = (
            f"<|im_start|>system\n{SYSTEM_PROMPT}<|im_end|>\n"
            f"<|im_start|>user\n{prompt}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )
        payload = {
            "inputs": full_prompt,
            "parameters": {
                "max_new_tokens":  MAX_NEW_TOKENS,
                "temperature":     0.7,
                "do_sample":       True,
                "return_full_text": False,   # devuelve SOLO la parte generada
            },
        }
        url = MODEL_API_URL

    # ── OpenAI-compatible (vLLM, LM Studio, llama.cpp server) ───────────────
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
            "max_tokens":  MAX_NEW_TOKENS,
            "temperature": 0.7,
        }
        url = f"{MODEL_API_URL.rstrip('/')}/v1/chat/completions"

    # ── Ollama ───────────────────────────────────────────────────────────────
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

    # ── Llamada al modelo ────────────────────────────────────────────────────
    try:
        async with httpx.AsyncClient(timeout=MODEL_TIMEOUT_S) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            res_json = response.json()

        # Extraer texto según proveedor
        if MODEL_PROVIDER in ("hf", "tgi"):
            if isinstance(res_json, list) and res_json:
                text = res_json[0].get("generated_text", "")
                # Seguridad: si por algún motivo viene el texto completo, extraer la parte del asistente
                if "<|im_start|>assistant" in text:
                    text = text.split("<|im_start|>assistant")[-1]
                    text = text.replace("<|im_end|>", "").strip()
                return text.strip() or "No pude generar una respuesta."
            # Algunos TGI locales devuelven dict directo
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


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    """Health-check para load balancers y monitorización de AWS."""
    return {
        "status":         "ok",
        "version":        "2.1.0",
        "model_provider": MODEL_PROVIDER,
        "model_url":      MODEL_API_URL,
    }


@app.get("/admin/history", response_model=list[BusquedaOut])
async def admin_history(
    db:      Session = Depends(get_db),
    id_info: dict    = Depends(verify_google_token),
):
    """Devuelve el historial de consultas (solo para administradores)."""
    admin_emails = ["gsoriano@iescomercio.com", "test@example.com"]
    if id_info["email"] not in admin_emails:
        raise HTTPException(status_code=403, detail="No tienes permisos de administrador")

    registros = db.query(Busqueda).order_by(Busqueda.creada_en.desc()).limit(500).all()

    # Serializar manualmente para Pydantic v2
    return [
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
    ]


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    query:   ChatQuery,
    db:      Session = Depends(get_db),
    id_info: dict    = Depends(verify_google_token),
) -> ChatResponse:
    """
    Flujo completo del chatbot RAG (Tareas 1 + 2):

      1. Filtro de contenido → rechazo inmediato sin llamar al modelo
      2. Recuperación RAG    → top-3 chunks de ChromaDB (async thread)
      3. Prompt enriquecido  → contexto + pregunta
      4. Inferencia async    → modelo local en AWS via httpx
      5. Logging Postgres    → anonimizado (Tarea 1) + métricas de tiempo
    """
    inicio_total = time.perf_counter()
    pregunta     = query.mensaje.strip()
    user_email   = id_info["email"]

    if not pregunta:
        return ChatResponse(
            respuesta="Escribe una consulta para poder ayudarte.",
            fuentes=[]
        )

    # ── 1. Filtro de contenido inapropiado ───────────────────────────────────
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

    # ── 2. Recuperación de contexto RAG ──────────────────────────────────────
    t_rag = time.perf_counter()
    contexto, fuentes_rag = await asyncio.to_thread(retrieve_context, pregunta)
    t_rag_ms = (time.perf_counter() - t_rag) * 1000
    logger.info(f"[RAG] {len(fuentes_rag)} fragmentos en {t_rag_ms:.1f}ms")

    # ── 3. Prompt enriquecido ─────────────────────────────────────────────────
    prompt = build_rag_prompt(pregunta, contexto)

    # ── 4. Registrar / actualizar usuario ────────────────────────────────────
    # Nota: guardamos el email REAL en la tabla users (solo para auth),
    # la tabla busquedas guarda el hash (Tarea 1).
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        db.add(User(
            email=user_email,
            name=id_info.get("name"),
            picture=id_info.get("picture"),
        ))
        try:
            db.commit()
        except Exception:
            db.rollback()

    # ── 5. Inferencia del modelo (async, no bloquea el event loop) ───────────
    t_modelo = time.perf_counter()
    respuesta = await query_model_async(prompt)
    t_modelo_ms = (time.perf_counter() - t_modelo) * 1000
    logger.info(f"[MODELO] Respuesta en {t_modelo_ms:.1f}ms")

    fuentes = fuentes_rag + [f"modelo:{MODEL_PROVIDER}"]

    tiempo_total_ms = (time.perf_counter() - inicio_total) * 1000
    logger.info(
        f"[TOTAL] {tiempo_total_ms:.1f}ms "
        f"(RAG={t_rag_ms:.0f}ms + modelo={t_modelo_ms:.0f}ms)"
    )

    # ── 6. Persistencia anonimizada en Postgres ───────────────────────────────
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