# --- Chatbot Plan Lector v2.0 (HF enabled) --- 

import os
import sys
import json
import time
import datetime
from pathlib import Path

import requests
import traceback
from fastapi import FastAPI, Depends, Header, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from database import SessionLocal, create_tables, Busqueda, User
from modelo.filtro import verificar_consulta

# Configuración Ollama
GOOGLE_CLIENT_ID = "22015513342-rp17v8jccio7gvnhkdma2vpigerrnu44.apps.googleusercontent.com"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")

create_tables()

app = FastAPI(title="LIA — Asistente del Plan Lector")


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
    idioma: str | None = "es"


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

def save_chat_to_db(user_email: str, session_id: str, pregunta: str, respuesta: str, fuentes: list, tiempo_ms: float):
    """Guarda el log de la consulta en la BD en segundo plano."""
    db = SessionLocal()
    try:
        db.add(Busqueda(
            user_email=user_email,
            session_id=session_id,
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
    finally:
        db.close()

def query_ollama_stream(prompt: str, idioma: str = "es"):
    """Genera respuesta usando Ollama local y la envía en stream."""
    system_msg = (
        "You are LIA, an expert assistant for the school Reading Plan. You help students with doubts about books and readings. Answer in English. "
        "You were created by four students from IES Comercio (Zaragoza, Spain) as a final project: "
        "Alexander Gavilanez Castro (https://www.linkedin.com/in/alexander-gavilanez-castro-037a8927b/), "
        "Iñigo del Mazo Monreal (https://www.linkedin.com/in/i%C3%B1igo-del-mazo-monreal-514a7a367), "
        "Diego Castilla Abella (https://www.linkedin.com/in/diego-castilla-abella-8892a319b/) and "
        "Alejandro Bueno Ortiz (https://www.linkedin.com/in/alejandro-bueno-ortiz-419054240/). "
        "If asked about your identity or creators, always mention all four of them with their LinkedIn profiles."
        if idioma == "en" else
        "Eres LIA, un asistente experto en el Plan Lector del centro. Ayudas a los alumnos con dudas sobre libros y lecturas. Responde siempre de forma amable. "
        "Fuiste creada por cuatro alumnos del IES Comercio (Zaragoza, España) como proyecto final: "
        "Alexander Gavilanez Castro (https://www.linkedin.com/in/alexander-gavilanez-castro-037a8927b/), "
        "Iñigo del Mazo Monreal (https://www.linkedin.com/in/i%C3%B1igo-del-mazo-monreal-514a7a367), "
        "Diego Castilla Abella (https://www.linkedin.com/in/diego-castilla-abella-8892a319b/) y "
        "Alejandro Bueno Ortiz (https://www.linkedin.com/in/alejandro-bueno-ortiz-419054240/). "
        "Si te preguntan quién eres o quién te ha creado, menciona siempre a los cuatro con sus perfiles de LinkedIn."
    )

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "system": system_msg,
        "stream": True,
        "options": {
            "temperature": 0.7
        }
    }
    
    try:
        with requests.post(OLLAMA_URL, json=payload, stream=True, timeout=30) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if line:
                    data = json.loads(line.decode('utf-8'))
                    yield data.get("response", "")
    except Exception as e:
        print(f"Error connecting to Ollama: {e}")
        yield " LIA no puede conectar con el motor local (Ollama). Por favor, asegúrate de que Ollama está ejecutándose en el servidor."






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

@app.delete("/chat/session/{session_id}")
async def delete_session(
    session_id: str, 
    db: Session = Depends(get_db), 
    id_info: dict = Depends(verify_google_token)
):
    """Borra todos los mensajes de una sesión específica."""
    user_email = id_info["email"]
    
    db.query(Busqueda).filter(
        Busqueda.user_email == user_email,
        Busqueda.session_id == session_id
    ).delete()
    
    db.commit()
    return {"status": "deleted"}

@app.post("/chat")
async def chat_endpoint(
    query: ChatQuery, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    id_info: dict = Depends(verify_google_token)
):
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

    # 2. Moderación de contenido (Filtro de toxicidad)
    resultado_filtro = verificar_consulta(pregunta)
    if not resultado_filtro["aceptado"]:
        # Registrar el bloqueo en Postgres
        db.add(Busqueda(
            user_email=user_email,
            session_id=query.session_id,
            pregunta=pregunta,
            respuesta=resultado_filtro["mensaje"],
            fuentes=json.dumps(["Filtro de Moderación"]),
            bloqueada=True,
            categoria_bloqueo=resultado_filtro.get("categoria"),
            tiempo_respuesta_ms=0,
        ))
        db.commit()
        return ChatResponse(respuesta=resultado_filtro["mensaje"], fuentes=[])

    # 3. Streaming de respuesta
    def response_generator():
        respuesta_completa = ""
        fuentes = ["Motor Local (Ollama)"]
        
        for chunk in query_ollama_stream(pregunta, query.idioma):
            respuesta_completa += chunk
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            
        tiempo_ms = (time.perf_counter() - inicio) * 1000
        yield f"data: {json.dumps({'done': True, 'fuentes': fuentes})}\n\n"
        
        background_tasks.add_task(
            save_chat_to_db, user_email, query.session_id, pregunta, respuesta_completa, fuentes, tiempo_ms
        )

    return StreamingResponse(
        response_generator(), 
        media_type="text/event-stream",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )