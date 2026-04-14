import os
import sys
import json
import time
import datetime
from pathlib import Path

import chromadb
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import SessionLocal, create_tables, Busqueda

# ── MongoDB (opcional — historial enriquecido) ─────────────────────────────
try:
    from pymongo import MongoClient
    _MONGO_URL = os.getenv("MONGODB_URL", "")
    _mongo_client = MongoClient(_MONGO_URL, serverSelectionTimeoutMS=3000) if _MONGO_URL else None
    _mongo_db = _mongo_client["planLectorDB"] if _mongo_client else None
    _chat_logs = _mongo_db["consultas"] if _mongo_db else None
    if _mongo_client:
        _mongo_client.admin.command("ping")
        print("MongoDB conectado correctamente.")
    else:
        print("MONGODB_URL no configurado — registro MongoDB desactivado.")
except Exception as _mongo_err:
    print(f"Conexión MongoDB fallida (no crítico): {_mongo_err}")
    _chat_logs = None

# ── Filtro de contenido inapropiado ───────────────────────────────────────
_MODELO_DIR = Path(__file__).resolve().parent / "modelo"
if str(_MODELO_DIR) not in sys.path:
    sys.path.insert(0, str(_MODELO_DIR))
from filtro import verificar_consulta  # noqa: E402

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


def get_chroma_paths() -> tuple[str, str]:
    base_dir = Path(__file__).resolve().parent.parent
    default_db = base_dir / "backend" / "datalake" / "artifacts" / "chroma_db"
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
        return "No he encontrado contexto suficiente para responder esa pregunta."

    fragmentos = []
    for doc in docs[:2]:
        limpio = " ".join(doc.split())
        fragmentos.append(limpio[:320])

    return " ".join(fragmentos).strip()


def registrar_en_mongodb(
    session_id: str | None,
    pregunta: str,
    respuesta: str,
    fuentes: list[str],
    bloqueada: bool,
    categoria_bloqueo: str | None,
    tiempo_ms: float,
):
    """Guarda la consulta completa en MongoDB como documento JSON."""
    if _chat_logs is None:
        return
    try:
        _chat_logs.insert_one({
            "session_id":         session_id,
            "pregunta":           pregunta,
            "respuesta":          respuesta,
            "fuentes":            fuentes,
            "bloqueada":          bloqueada,
            "categoria_bloqueo":  categoria_bloqueo,
            "tiempo_respuesta_ms": tiempo_ms,
            "fecha":              datetime.datetime.utcnow(),
        })
    except Exception as e:
        print(f"Error al guardar en MongoDB (no crítico): {e}")


@app.get("/")
def read_root():
    return {"mensaje": "API del Plan Lector operativa"}


@app.post("/chat")
async def chat_endpoint(query: ChatQuery, db: Session = Depends(get_db)) -> ChatResponse:
    inicio = time.perf_counter()
    pregunta = query.mensaje.strip()

    if not pregunta:
        return ChatResponse(respuesta="Escribe una consulta para poder ayudarte.", fuentes=[])

    # ── 1. Filtro de contenido ────────────────────────────────────────────
    verificacion = verificar_consulta(pregunta)
    if not verificacion["aceptado"]:
        tiempo_ms = (time.perf_counter() - inicio) * 1000
        categoria = verificacion.get("categoria", "desconocido")
        msg = verificacion["mensaje"]

        # PostgreSQL
        db.add(Busqueda(
            session_id=query.session_id,
            pregunta=pregunta,
            respuesta=msg,
            fuentes="[]",
            bloqueada=True,
            categoria_bloqueo=categoria,
            tiempo_respuesta_ms=tiempo_ms,
        ))
        db.commit()

        # MongoDB
        registrar_en_mongodb(query.session_id, pregunta, msg, [], True, categoria, tiempo_ms)
        return ChatResponse(respuesta=msg, fuentes=[])

    # ── 2. Recuperar contexto vectorial (ChromaDB) ────────────────────────
    try:
        docs, fuentes = recuperar_contexto(pregunta)
        respuesta = generar_respuesta(pregunta, docs)
    except Exception as e:
        import traceback
        print("ERROR EN RECUPERAR_CONTEXTO:", e)
        traceback.print_exc()
        respuesta = "Ahora mismo no puedo consultar el índice de contexto. Inténtalo de nuevo."
        fuentes = []

    tiempo_ms = (time.perf_counter() - inicio) * 1000

    # ── 3. Registrar en PostgreSQL (tabla busquedas) ──────────────────────
    db.add(Busqueda(
        session_id=query.session_id,
        pregunta=pregunta,
        respuesta=respuesta,
        fuentes=json.dumps(fuentes),
        bloqueada=False,
        tiempo_respuesta_ms=tiempo_ms,
    ))
    db.commit()

    # ── 4. Registrar en MongoDB (historial enriquecido) ───────────────────
    registrar_en_mongodb(query.session_id, pregunta, respuesta, fuentes, False, None, tiempo_ms)

    return ChatResponse(respuesta=respuesta, fuentes=fuentes)