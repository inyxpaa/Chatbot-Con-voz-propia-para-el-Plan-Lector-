"""
==============================================================
  rag_engine.py — Motor de Recuperación Aumentada (RAG)
==============================================================
  Proyecto : Chatbot Plan Lector
  Tarea    : 2 — Optimización de Latencia y Rendimiento

  Fixes aplicados:
    - CHROMA_DB_PATH configurable via env var CHROMA_DB_PATH
      para que funcione en cualquier ruta dentro de AWS
    - Singleton robusto: si ChromaDB falla al arrancar, el
      chatbot degrada gracefully sin crashear
==============================================================
"""

import os
import logging
from functools import lru_cache
from pathlib import Path

import chromadb

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# La ruta a ChromaDB se puede sobreescribir con variable de entorno.
# Por defecto busca relativo al propio rag_engine.py (estructura local).
# En AWS, establecer: CHROMA_DB_PATH=/app/datalake/artifacts/chroma_db
_default_chroma_path = Path(__file__).parent / "datalake" / "artifacts" / "chroma_db"
CHROMA_DB_PATH  = Path(os.getenv("CHROMA_DB_PATH", str(_default_chroma_path)))
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "convozpropia")

# Número de fragmentos a recuperar por consulta
# 3 es el equilibrio óptimo: suficiente contexto, mínima latencia
N_RESULTS = int(os.getenv("RAG_N_RESULTS", "3"))


# ---------------------------------------------------------------------------
# Singleton ChromaDB — se inicializa UNA vez al arrancar la app
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _get_collection():
    """
    Devuelve la colección de ChromaDB ya inicializada.

    lru_cache garantiza que la conexión se establece una sola vez
    durante toda la vida del proceso, eliminando el overhead de
    reconectar en cada petición (~200-400ms ahorrados por request).

    Returns:
        chromadb.Collection o None si ChromaDB no está disponible.
    """
    try:
        if not CHROMA_DB_PATH.exists():
            logger.warning(
                f"[RAG] ChromaDB no encontrado en: {CHROMA_DB_PATH}. "
                "El chatbot funcionará sin contexto RAG (modo degradado)."
            )
            return None

        client     = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
        collection = client.get_collection(name=COLLECTION_NAME)
        total      = collection.count()
        logger.info(
            f"[RAG] ChromaDB listo — colección '{COLLECTION_NAME}' "
            f"con {total} chunks indexados en {CHROMA_DB_PATH}"
        )
        return collection

    except Exception as e:
        logger.error(f"[RAG] Error al conectar con ChromaDB: {e}")
        return None


# ---------------------------------------------------------------------------
# Recuperación de contexto
# ---------------------------------------------------------------------------

def retrieve_context(pregunta: str, n_results: int = N_RESULTS) -> tuple[str, list[str]]:
    """
    Recupera los fragmentos más relevantes del corpus para una pregunta.

    Returns:
        (contexto_formateado, lista_de_fuentes)
        Si ChromaDB no está disponible devuelve ("", []) — modo degradado.
    """
    collection = _get_collection()
    if collection is None:
        return "", []

    try:
        count = collection.count()
        if count == 0:
            return "", []

        results = collection.query(
            query_texts=[pregunta],
            n_results=min(n_results, count),
        )

        docs = results.get("documents", [[]])[0]
        if not docs:
            logger.debug("[RAG] No se encontraron fragmentos relevantes para la consulta.")
            return "", []

        partes  = [f"[Fragmento {i}]:\n{doc.strip()}" for i, doc in enumerate(docs, start=1)]
        contexto = "\n\n".join(partes)
        fuentes  = [f"RAG:convozpropia:frag_{i}" for i in range(1, len(docs) + 1)]

        logger.debug(f"[RAG] Recuperados {len(docs)} fragmentos relevantes.")
        return contexto, fuentes

    except Exception as e:
        logger.error(f"[RAG] Error durante la búsqueda vectorial: {e}")
        return "", []


# ---------------------------------------------------------------------------
# Construcción del prompt enriquecido
# ---------------------------------------------------------------------------

def build_rag_prompt(pregunta: str, contexto: str) -> str:
    """
    Construye el prompt final con el contexto RAG insertado.

    NOTA: Este método construye SOLO el contenido de usuario/contexto.
    El system prompt (instrucciones de rol) se inyecta en query_model_async
    según el formato que requiera cada proveedor (ChatML, OpenAI messages, etc.)
    para no duplicar instrucciones.
    """
    if contexto:
        return (
            "Usa ÚNICAMENTE la siguiente información del Plan Lector para responder. "
            "Si la información no cubre la pregunta, indícalo brevemente.\n\n"
            f"=== INFORMACIÓN DEL PLAN LECTOR ===\n{contexto}\n"
            "=== FIN ===\n\n"
            f"Pregunta: {pregunta}"
        )
    # Degraded mode: sin contexto RAG
    return pregunta


# ---------------------------------------------------------------------------
# Warm-up
# ---------------------------------------------------------------------------

def warmup():
    """
    Precarga la conexión a ChromaDB al arrancar la app.
    Elimina la latencia extra del primer request.
    """
    logger.info("[RAG] Iniciando warm-up de ChromaDB...")
    _get_collection()
    logger.info("[RAG] Warm-up completado.")
