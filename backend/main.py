import os
import sys
import datetime
from pathlib import Path

import chromadb
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import SessionLocal, create_tables, Interaction

# ── MongoDB (optional – logs rich chat history) ───────────────────────────
try:
    from pymongo import MongoClient
    _MONGO_URL = os.getenv("MONGODB_URL", "")
    _mongo_client = MongoClient(_MONGO_URL, serverSelectionTimeoutMS=3000) if _MONGO_URL else None
    _mongo_db = _mongo_client["planLectorDB"] if _mongo_client else None
    _chat_logs = _mongo_db["chat_logs"] if _mongo_db else None
    if _mongo_client:
        _mongo_client.admin.command("ping")  # verify connection
        print("MongoDB connected.")
    else:
        print("MONGODB_URL not set — MongoDB logging disabled.")
except Exception as _mongo_err:
    print(f"MongoDB connection failed (non-fatal): {_mongo_err}")
    _chat_logs = None

# ── Filtro de contenido (insultos, racismo, odio) ─────────────────
# Añade modelo/ al path para poder importar filtro.py directamente
_MODELO_DIR = Path(__file__).resolve().parent / "modelo"
if str(_MODELO_DIR) not in sys.path:
    sys.path.insert(0, str(_MODELO_DIR))
from filtro import verificar_consulta  # noqa: E402

create_tables()

app = FastAPI(title="Chatbot 'Con voz propia' API")

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

    contexto = " ".join(fragmentos).strip()
    return contexto


@app.get("/")
def read_root():
    return {"mensaje": "API del Plan Lector operativa"}


@app.post("/chat")
async def chat_endpoint(query: ChatQuery, db: Session = Depends(get_db)) -> ChatResponse:
    pregunta = query.mensaje.strip()
    if not pregunta:
        return ChatResponse(respuesta="Escribe una consulta para poder ayudarte.", fuentes=[])

    # ── 1. Filtro de contenido inapropiado ───────────────────────────
    verificacion = verificar_consulta(pregunta)
    if not verificacion["aceptado"]:
        # Guardamos el intento en BD igualmente (para auditoría)
        new_log = Interaction(
            session_id=query.session_id,
            question=pregunta,
            answer=f"[BLOQUEADO:{verificacion['categoria']}] {verificacion['mensaje']}"
        )
        db.add(new_log)
        db.commit()
        return ChatResponse(respuesta=verificacion["mensaje"], fuentes=[])
    # ─────────────────────────────────────────────────────────────────

    # ── 2. Recuperar contexto del índice vectorial ───────────────────
    try:
        docs, fuentes = recuperar_contexto(pregunta)
        respuesta = generar_respuesta(pregunta, docs)
    except Exception as e:
        import traceback
        print("ERROR EN RECUPERAR_CONTEXTO:", e)
        traceback.print_exc()
        respuesta = "Ahora mismo no puedo consultar el índice de contexto. Inténtalo de nuevo."
        fuentes = []

    # ── 3. Registrar en PostgreSQL ────────────────────────────────────
    new_log = Interaction(session_id=query.session_id, question=pregunta, answer=respuesta)
    db.add(new_log)
    db.commit()

    # ── 4. Registrar en MongoDB (historial rico) ──────────────────────
    if _chat_logs is not None:
        try:
            _chat_logs.insert_one({
                "session_id": query.session_id,
                "question": pregunta,
                "answer": respuesta,
                "sources": fuentes,
                "timestamp": datetime.datetime.utcnow(),
            })
        except Exception as mongo_err:
            print(f"MongoDB log failed (non-fatal): {mongo_err}")

    return ChatResponse(respuesta=respuesta, fuentes=fuentes)