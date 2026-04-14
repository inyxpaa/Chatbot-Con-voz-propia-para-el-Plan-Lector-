import os
from pathlib import Path
import chromadb
from sqlalchemy.orm import Session
from pydantic import BaseModel
from google.oauth2 import id_token
from google.auth.transport import requests
from fastapi import FastAPI, Depends, HTTPException, Header
from .database import SessionLocal, create_tables, Interaction, User, RedFlag

# Importamos lo que creamos en database.py
from .database import SessionLocal, create_tables, Interaction, User, RedFlag


# Iniciamos las tablas al arrancar
create_tables()


app = FastAPI(title="Chatbot 'Con voz propia' API")


# --- SEGURIDAD ---
GOOGLE_CLIENT_ID = "TU_CLIENT_ID_DE_GOOGLE.apps.googleusercontent.com"


def obtener_usuario_google(token_google: str = Header(None)):
    if not token_google:
        raise HTTPException(status_code=401, detail="Se requiere inicio de sesión con Google")
    try:
        # En el futuro, aquí validaremos con el GOOGLE_CLIENT_ID real
        idinfo = id_token.verify_oauth2_token(token_google, requests.Request(), GOOGLE_CLIENT_ID)
        return idinfo['email']
    except Exception:
        # Para que puedas probarlo ahora sin tener el ID de Google todavía:
        # Si pones "token-de-prueba" en el header, te dejará pasar (SOLO PARA DESARROLLO)
        if token_google == "token-de-prueba":
            return "usuario_prueba@iescomercio.com"
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada")


# --- MODELOS DE DATOS ---
class ChatQuery(BaseModel):
    mensaje: str


class ChatResponse(BaseModel):
    respuesta: str
    fuentes: list[str]


# --- DEPENDENCIAS ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- LÓGICA DE CHROMADB (Mantenemos lo que ya tenías) ---
def get_chroma_paths() -> tuple[str, str]:
    base_dir = Path(__file__).resolve().parent.parent
    default_db = base_dir / "backend" / "datalake" / "datalake" / "artifacts" / "chroma_db"
    db_path = os.getenv("CHROMA_DB_PATH", str(default_db))
    collection_name = os.getenv("CHROMA_COLLECTION", "quijote")
    return db_path, collection_name


def recuperar_contexto(pregunta: str, top_k: int = 3) -> tuple[list[str], list[str]]:
    db_path, collection_name = get_chroma_paths()
    cliente = chromadb.PersistentClient(path=db_path)
    coleccion = cliente.get_collection(name=collection_name)
    resultados = coleccion.query(query_texts=[pregunta], n_results=top_k)
    docs = resultados.get("documents", [[]])[0]
    return docs, [f"chroma:{collection_name}"]


def generar_respuesta(pregunta: str, docs: list[str]) -> str:
    if not docs:
        return "No he encontrado contexto suficiente."
    contexto = " ".join(docs[:2]).strip()
    return contexto


# --- ENDPOINTS ---
@app.get("/")
def read_root():
    return {"mensaje": "API del Plan Lector operativa con Seguridad"}


@app.post("/chat")
async def chat_endpoint(
    query: ChatQuery,
    db: Session = Depends(get_db),
    user_email: str = Depends(obtener_usuario_google)
) -> ChatResponse:
   
    pregunta = query.mensaje.strip()
   
    # 1. FILTRO DE TOXICIDAD (Simulado)
    palabras_prohibidas = ["tonto", "feo", "insulto123"]
    if any(p in pregunta.lower() for p in palabras_prohibidas):
        # Guardamos la infracción
        nueva_infraccion = RedFlag(user_email=user_email, content=pregunta)
        db.add(nueva_infraccion)
        db.commit()
        return ChatResponse(
            respuesta="Se ha detectado lenguaje inapropiado. Tu consulta ha sido registrada.",
            fuentes=[]
        )


    # 2. PROCESAMIENTO NORMAL
    try:
        docs, fuentes = recuperar_contexto(pregunta)
        respuesta = generar_respuesta(pregunta, docs)
    except Exception as e:
        respuesta = "Error técnico al consultar el contexto."
        fuentes = []


    # 3. GUARDAR INTERACCIÓN
    new_log = Interaction(
        user_email=user_email,
        question=pregunta,
        answer=respuesta
    )
    db.add(new_log)
    db.commit()


    return ChatResponse(respuesta=respuesta, fuentes=fuentes)
