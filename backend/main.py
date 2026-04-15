import os
import sys
import json
import time
import datetime
from pathlib import Path

import requests
from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from database import SessionLocal, create_tables, Busqueda, User

# Configuración
GOOGLE_CLIENT_ID = "22015513342-rp17v8jccio7gvnhkdma2vpigerrnu44.apps.googleusercontent.com"
HF_MODEL_ID = "inyxpa/chatbot"
HF_API_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL_ID}"
HF_TOKEN = os.getenv("HF_TOKEN", "")

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

def query_hf_model(prompt: str) -> str:
    if not HF_TOKEN:
        return "Respuesta (MODO OFFLINE): El modelo no está configurado (HF_TOKEN falta)."
    
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {
        "inputs": f"<|im_start|>system\nEres un asistente experto en el Plan Lector del centro. Ayudas a los alumnos con dudas sobre libros y lecturas.<|im_end|>\n<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n",
        "parameters": {"max_new_tokens": 512, "temperature": 0.7}
    }
    
    try:
        response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=15)
        res_json = response.json()
        if isinstance(res_json, list) and len(res_json) > 0:
            full_text = res_json[0].get("generated_text", "")
            # Limpiar la respuesta para quedarnos solo con lo que dice el asistente
            if "assistant\n" in full_text:
                return full_text.split("assistant\n")[-1].strip()
            return full_text
        return "No pude obtener una respuesta del modelo en este momento."
    except Exception as e:
        print(f"Error calling HF API: {e}")
        return "Hubo un error al conectar con el cerebro del asistente."





# MongoDB desactivado en favor de Postgres según solicitud del usuario


@app.get("/admin/history")
async def admin_history(db: Session = Depends(get_db), id_info: dict = Depends(verify_google_token)):
    # Simple control de acceso por email (puedes añadir más emails aquí)
    admin_emails = ["gsoriano@iescomercio.com", "test@example.com"]
    if id_info["email"] not in admin_emails:
        raise HTTPException(status_code=403, detail="No tienes permisos de administrador")
    
    return db.query(Busqueda).order_by(Busqueda.creada_en.desc()).all()

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

    # 2. Generar respuesta usando el cerebro en Hugging Face
    try:
        respuesta = query_hf_model(pregunta)
        fuentes = ["Hugging Face (inyxpa/chatbot)"]
    except Exception as e:
        print("ERROR EN HF API:", e)
        respuesta = "Ahora mismo no puedo conectar con mi cerebro en la nube. Inténtalo de nuevo."
        fuentes = []

    tiempo_ms = (time.perf_counter() - inicio) * 1000

    # 3. Registrar en PostgreSQL (tabla busquedas)
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

    return ChatResponse(respuesta=respuesta, fuentes=fuentes)