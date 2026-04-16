# --- Chatbot Plan Lector v2.0 (HF enabled) ---
import os
import sys
import json
import time
import datetime
from pathlib import Path

import requests
import torch
import psutil
import traceback
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from database import SessionLocal, create_tables, Busqueda, User

# Configuración
GOOGLE_CLIENT_ID = "22015513342-rp17v8jccio7gvnhkdma2vpigerrnu44.apps.googleusercontent.com"
HF_MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct" 
HF_ADAPTER_ID = "inyxpa/chatbot"
HF_TOKEN = os.getenv("HF_TOKEN", "")

# Variables globales para el modelo local (se cargan al inicio)
assistant_model = None
assistant_tokenizer = None

create_tables()

app = FastAPI(title="API del Chatbot 'Con voz propia' — Plan Lector")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatQuery(BaseModel):
    mensaje: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    respuesta: str
    fuentes: list[str]


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_google_token(authorization: str = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No se proporcionó token de sesión")
    
    token = authorization.split(" ")[1]
    
    # Bypass para pruebas si el token es "token-de-prueba" (solo para desarrollo)
    if token == "token-de-prueba":
        return {"email": "test@example.com", "name": "Test User", "picture": ""}
        
    try:
        idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), GOOGLE_CLIENT_ID)
        return idinfo
    except Exception as e:
        print(f"Error validando token: {e}")
        raise HTTPException(status_code=401, detail="Token de Google inválido")

def query_local_model(prompt: str) -> str:
    """Genera respuesta usando el modelo cargado en memoria local."""
    global assistant_model, assistant_tokenizer
    
    if assistant_model is None or assistant_tokenizer is None:
        return "El cerebro del asistente aún se está cargando o no se pudo cargar. Prueba en unos segundos."
        
    try:
        # Check memory before starting
        mem = psutil.virtual_memory()
        print(f"Generando respuesta... Memoria disponible: {mem.available / (1024**2):.2f} MB")

        messages = [
            {"role": "system", "content": "Eres un asistente experto en el Plan Lector del centro. Ayudas a los alumnos con dudas sobre libros y lecturas."},
            {"role": "user", "content": prompt}
        ]
        
        # Aplicar el chat template del modelo
        inputs = assistant_tokenizer.apply_chat_template(
            messages, 
            add_generation_prompt=True, 
            return_tensors="pt",
            return_dict=True
        ).to("cpu")
        
        # Generar (limitar el tamaño para evitar OOM si es necesario)
        with torch.no_grad():
            outputs = assistant_model.generate(
                inputs["input_ids"],
                attention_mask=inputs.get("attention_mask"),
                max_new_tokens=256, # Reducido de 512 para probar estabilidad
                do_sample=True, 
                temperature=0.7,
                pad_token_id=assistant_tokenizer.eos_token_id
            )
        
        # Omitir los tokens de entrada de la respuesta
        input_length = inputs["input_ids"].shape[-1]
        decoded = assistant_tokenizer.decode(outputs[0][input_length:], skip_special_tokens=True)
        return decoded.strip()
            
    except Exception as e:
        print(f"Error en inferencia local:")
        print(traceback.format_exc())
        return f"Hubo un error al procesar tu duda localmente: {str(e)}"

@app.on_event("startup")
async def startup_event():
    """Carga el modelo de IA al iniciar el servidor."""
    global assistant_model, assistant_tokenizer
    
    print("Iniciando carga del modelo local...")
    try:
        # Cargar Tokenizer
        assistant_tokenizer = AutoTokenizer.from_pretrained(HF_MODEL_ID)
        
        # Cargar Modelo base en Float16 para ahorrar RAM
        print(f"Cargando modelo base {HF_MODEL_ID}...")
        base_model = AutoModelForCausalLM.from_pretrained(
            HF_MODEL_ID,
            torch_dtype=torch.float16,
            low_cpu_mem_usage=True,
            device_map="cpu"
        )
        
        # Cargar el adaptador LoRA
        print(f"Cargando adaptador {HF_ADAPTER_ID}...")
        assistant_model = PeftModel.from_pretrained(base_model, HF_ADAPTER_ID)
        assistant_model.eval() # Poner en modo evaluación
        
        print("¡Modelo cargado y listo para usar localmente!")
    except Exception:
        print(f"FATAL: No se pudo cargar el modelo local al inicio:")
        print(traceback.format_exc())





# MongoDB desactivado en favor de Postgres según solicitud del usuario


@app.get("/admin/history")
async def admin_history(db: Session = Depends(get_db), id_info: dict = Depends(verify_google_token)):
    # Control de acceso por email
    admin_emails = [
        "gsoriano@iescomercio.com", 
        "lentejasricas@gmail.com", 
        "dcastillaa@gmail.com",
        "test@example.com"
    ]
    if id_info["email"] not in admin_emails:
        raise HTTPException(status_code=403, detail="No tienes permisos de administrador")
    
    return db.query(Busqueda).order_by(Busqueda.creada_en.desc()).all()

@app.get("/chat/sessions")
async def get_user_sessions(db: Session = Depends(get_db), id_info: dict = Depends(verify_google_token)):
    """Obtiene la lista de sesiones únicas del usuario con un resumen."""
    user_email = id_info["email"]
    
    # Obtener la primera pregunta de cada sesión para usarla como título
    from sqlalchemy import func
    
    # Subconsulta para obtener el ID mínimo (primera consulta) de cada sesión
    subq = db.query(
        Busqueda.session_id,
        func.min(Busqueda.id).label("min_id")
    ).filter(Busqueda.user_email == user_email).group_by(Busqueda.session_id).subquery()
    
    # Unir con la tabla original para tener el texto de la pregunta
    sessions = db.query(
        Busqueda.session_id,
        Busqueda.pregunta.label("titulo"),
        Busqueda.creada_en
    ).join(subq, Busqueda.id == subq.c.min_id).order_by(Busqueda.creada_en.desc()).all()
    
    return [{"session_id": s.session_id, "titulo": s.titulo[:40] + "...", "fecha": s.creada_en} for s in sessions]

@app.get("/chat/history/{session_id}")
async def get_session_history(
    session_id: str, 
    db: Session = Depends(get_db), 
    id_info: dict = Depends(verify_google_token)
):
    """Obtiene todos los mensajes de una sesión específica filtrando por usuario."""
    user_email = id_info["email"]
    
    messages = db.query(Busqueda).filter(
        Busqueda.user_email == user_email,
        Busqueda.session_id == session_id
    ).order_by(Busqueda.creada_en.asc()).all()
    
    return messages

@app.post("/chat")
async def chat_endpoint(
    query: ChatQuery, 
    db: Session = Depends(get_db),
    id_info: dict = Depends(verify_google_token)
) -> ChatResponse:
    inicio = time.perf_counter()
    pregunta = query.mensaje.strip()
    user_email = id_info["email"]

    if not pregunta:
        return ChatResponse(respuesta="Escribe una consulta para poder ayudarte.", fuentes=[])

    # 1. Registrar o actualizar usuario
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        user = User(email=user_email, name=id_info.get("name"), picture=id_info.get("picture"))
        db.add(user)
        db.commit()

    # 2. Generar respuesta usando el modelo local
    try:
        respuesta = query_local_model(pregunta)
        fuentes = ["IA Local (Qwen 1.5B + Adapter)"]
    except Exception as e:
        print("ERROR EN INFERENCIA LOCAL:", e)
        respuesta = "Ahora mismo no puedo procesar tu duda localmente. Inténtalo de nuevo."
        fuentes = []

    tiempo_ms = (time.perf_counter() - inicio) * 1000

    # 3. Registrar en PostgreSQL (tabla busquedas)
    try:
        db.add(Busqueda(
            user_email=user_email,
            session_id=query.session_id,
            pregunta=pregunta,
            respuesta=respuesta,
            fuentes=json.dumps(fuentes),
            bloqueada=False,
            tiempo_respuesta_ms=tiempo_ms,
        ))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"FATAL: Error al guardar en Postgres: {e}")

    return ChatResponse(respuesta=respuesta, fuentes=fuentes)