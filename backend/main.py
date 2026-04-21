# --- Chatbot Plan Lector v2.1 (RAG activado + modelo local AWS) ---
import os
import sys
import json
import time
import logging
import datetime
import hashlib
import re
import asyncio
from pathlib import Path

import httpx
import requests
from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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
# Configuración
# ---------------------------------------------------------------------------

GOOGLE_CLIENT_ID = "22015513342-rp17v8jccio7gvnhkdma2vpigerrnu44.apps.googleusercontent.com"

# ── Modelo: URL configurable por variable de entorno ────────────────────────
# Para el modelo LOCAL en la instancia AWS, establece en .env / systemd:
#   MODEL_API_URL=http://localhost:8080
# Para Ollama local:
#   MODEL_API_URL=http://localhost:11434/api/generate
#   MODEL_PROVIDER=ollama
# Por defecto apunta a la API de Hugging Face (fallback)
HF_MODEL_ID  = "inyxpa/chatbot"
HF_API_URL   = f"https://api-inference.huggingface.co/models/{HF_MODEL_ID}"
HF_TOKEN     = os.getenv("HF_TOKEN", "")

MODEL_API_URL = os.getenv("MODEL_API_URL", HF_API_URL)
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "hf").lower()
# Valores válidos para MODEL_PROVIDER: "hf" | "tgi" | "ollama" | "openai"

# Parámetros de generación
MAX_NEW_TOKENS  = int(os.getenv("MAX_NEW_TOKENS", "256"))   # reducido de 512→256 para menor latencia
MODEL_TIMEOUT_S = int(os.getenv("MODEL_TIMEOUT_S", "30"))   # timeout configurable

# ---------------------------------------------------------------------------
# Inicialización
# ---------------------------------------------------------------------------

create_tables()
warmup()  # Precarga ChromaDB al arrancar → elimina latencia del primer request

app = FastAPI(title="API del Chatbot 'Con voz propia' — Plan Lector v2.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Utilidades de privacidad (Tarea 1)
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
    text = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '[EMAIL]', text)
    text = re.sub(r'\+?\d{2,4}[-.‌\s]?\d{3,4}[-.‌\s]?\d{3,4}[-.‌\s]?\d{0,4}', '[TELÉFONO]', text)
    return text


# ---------------------------------------------------------------------------
# Modelos Pydantic
# ---------------------------------------------------------------------------

class ChatQuery(BaseModel):
    mensaje: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    respuesta: str
    fuentes: list[str]


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

    # Bypass para pruebas (solo en desarrollo)
    if token == "token-de-prueba":
        return {"email": "test@example.com", "name": "Test User", "picture": ""}

    try:
        idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), GOOGLE_CLIENT_ID)
        return idinfo
    except Exception as e:
        logger.warning(f"Token inválido: {e}")
        raise HTTPException(status_code=401, detail="Token de Google inválido")


# ---------------------------------------------------------------------------
# Inferencia del modelo — multi-proveedor
# ---------------------------------------------------------------------------

async def query_model_async(prompt: str) -> str:
    """
    Llama al modelo LLM de forma asíncrona usando httpx.

    Soporta varios proveedores según MODEL_PROVIDER:
      - "hf"     : HF Inference API (cloud o TGI con mismo formato)
      - "tgi"    : Text Generation Inference local (mismo formato que HF)
      - "openai" : API compatible con OpenAI (vLLM, LM Studio, etc.)
      - "ollama" : Ollama local

    La URL del endpoint se controla mediante MODEL_API_URL.
    """
    headers = {}
    payload  = {}

    if MODEL_PROVIDER in ("hf", "tgi"):
        # ── HF Inference API / TGI ───────────────────────────────────────
        if HF_TOKEN:
            headers["Authorization"] = f"Bearer {HF_TOKEN}"
        payload = {
            "inputs": (
                f"<|im_start|>system\n"
                f"Eres un asistente experto en el Plan Lector del centro. "
                f"Ayudas a los alumnos con dudas sobre libros y lecturas."
                f"<|im_end|>\n"
                f"<|im_start|>user\n{prompt}<|im_end|>\n"
                f"<|im_start|>assistant\n"
            ),
            "parameters": {
                "max_new_tokens": MAX_NEW_TOKENS,
                "temperature": 0.7,
                "do_sample": True,
                "return_full_text": False,  # solo la parte nueva
            },
        }
        url = MODEL_API_URL

    elif MODEL_PROVIDER == "openai":
        # ── OpenAI-compatible (vLLM, LM Studio) ─────────────────────────
        if HF_TOKEN:
            headers["Authorization"] = f"Bearer {HF_TOKEN}"
        headers["Content-Type"] = "application/json"
        payload = {
            "model": os.getenv("MODEL_NAME", HF_MODEL_ID),
            "messages": [
                {"role": "system", "content": "Eres un asistente experto en el Plan Lector."},
                {"role": "user",   "content": prompt},
            ],
            "max_tokens": MAX_NEW_TOKENS,
            "temperature": 0.7,
        }
        url = f"{MODEL_API_URL}/v1/chat/completions"

    elif MODEL_PROVIDER == "ollama":
        # ── Ollama ───────────────────────────────────────────────────────
        payload = {
            "model": os.getenv("MODEL_NAME", "qwen"),
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": MAX_NEW_TOKENS, "temperature": 0.7},
        }
        url = f"{MODEL_API_URL}/api/generate"

    else:
        return f"Error: MODEL_PROVIDER '{MODEL_PROVIDER}' no reconocido."

    try:
        async with httpx.AsyncClient(timeout=MODEL_TIMEOUT_S) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            res_json = response.json()

        # Extraer la respuesta según el proveedor
        if MODEL_PROVIDER in ("hf", "tgi"):
            if isinstance(res_json, list) and res_json:
                # Con return_full_text=False, ya viene solo la parte del asistente
                text = res_json[0].get("generated_text", "")
                # Por si acaso, limpiar el prefijo del asistente si viene
                if "assistant\n" in text:
                    text = text.split("assistant\n")[-1]
                return text.strip()
            return "No pude obtener una respuesta del modelo."

        elif MODEL_PROVIDER == "openai":
            choices = res_json.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "").strip()
            return "No pude obtener una respuesta del modelo."

        elif MODEL_PROVIDER == "ollama":
            return res_json.get("response", "").strip()

    except httpx.TimeoutException:
        logger.error(f"Timeout ({MODEL_TIMEOUT_S}s) al conectar con el modelo en {url}")
        return "El asistente tardó demasiado en responder. Por favor, inténtalo de nuevo."
    except httpx.HTTPStatusError as e:
        logger.error(f"Error HTTP {e.response.status_code} del modelo: {e.response.text[:200]}")
        return "Hubo un error al conectar con el cerebro del asistente."
    except Exception as e:
        logger.error(f"Error inesperado en query_model_async: {e}")
        return "Hubo un error al conectar con el cerebro del asistente."


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    """Health-check rápido para load balancers y monitorización."""
    return {"status": "ok", "version": "2.1", "model_provider": MODEL_PROVIDER}


@app.get("/admin/history")
async def admin_history(
    db: Session = Depends(get_db),
    id_info: dict = Depends(verify_google_token),
):
    admin_emails = ["gsoriano@iescomercio.com", "test@example.com"]
    if id_info["email"] not in admin_emails:
        raise HTTPException(status_code=403, detail="No tienes permisos de administrador")
    return db.query(Busqueda).order_by(Busqueda.creada_en.desc()).all()


@app.post("/chat")
async def chat_endpoint(
    query: ChatQuery,
    db: Session = Depends(get_db),
    id_info: dict = Depends(verify_google_token),
) -> ChatResponse:
    """
    Flujo optimizado del endpoint /chat (Tarea 2):

      1. Filtro de contenido inapropiado → rechazo rápido sin tocar el modelo
      2. ChromaDB RAG en paralelo       → contexto relevante sin bloquear
      3. Prompt enriquecido             → respuestas más cortas y precisas
      4. Inferencia async (httpx)       → no bloquea el event loop de FastAPI
      5. Registro anonimizado en Postgres con métricas de tiempo
    """
    inicio_total = time.perf_counter()
    pregunta     = query.mensaje.strip()
    user_email   = id_info["email"]

    if not pregunta:
        return ChatResponse(respuesta="Escribe una consulta para poder ayudarte.", fuentes=[])

    # ── 1. Filtro de contenido ────────────────────────────────────────────
    resultado_filtro = verificar_consulta(pregunta)
    if not resultado_filtro["aceptado"]:
        # Rechazado: registramos pero no llamamos al modelo
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
            logger.error(f"Error al registrar consulta bloqueada: {e}")

        return ChatResponse(respuesta=resultado_filtro["mensaje"], fuentes=[])

    # ── 2. RAG: recuperar contexto de ChromaDB ────────────────────────────
    # Se ejecuta en un thread separado para no bloquear el event loop
    t_rag_inicio = time.perf_counter()
    contexto, fuentes_rag = await asyncio.to_thread(retrieve_context, pregunta)
    t_rag_ms = (time.perf_counter() - t_rag_inicio) * 1000
    logger.info(f"[RAG] Contexto recuperado en {t_rag_ms:.1f}ms — {len(fuentes_rag)} fragmentos")

    # ── 3. Construir prompt enriquecido ───────────────────────────────────
    prompt = build_rag_prompt(pregunta, contexto)

    # ── 4. Registrar o actualizar usuario ─────────────────────────────────
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        user = User(
            email=user_email,
            name=id_info.get("name"),
            picture=id_info.get("picture"),
        )
        db.add(user)
        db.commit()

    # ── 5. Inferencia async del modelo ────────────────────────────────────
    t_modelo_inicio = time.perf_counter()
    respuesta = await query_model_async(prompt)
    t_modelo_ms = (time.perf_counter() - t_modelo_inicio) * 1000
    logger.info(f"[MODELO] Respuesta generada en {t_modelo_ms:.1f}ms")

    # Fuentes finales: RAG + proveedor del modelo
    fuentes = fuentes_rag if fuentes_rag else []
    fuentes.append(f"modelo:{MODEL_PROVIDER}")

    tiempo_total_ms = (time.perf_counter() - inicio_total) * 1000
    logger.info(f"[TOTAL] Request completado en {tiempo_total_ms:.1f}ms "
                f"(RAG={t_rag_ms:.0f}ms, modelo={t_modelo_ms:.0f}ms)")

    # ── 6. Registrar en Postgres (anonimizado) ────────────────────────────
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