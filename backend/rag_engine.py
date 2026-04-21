"""
==============================================================
  rag_engine.py — Motor de Recuperación Aumentada (RAG)
==============================================================
  Proyecto : Chatbot Plan Lector
  Tarea    : 2 — Optimización de Latencia y Rendimiento

  Responsabilidades:
    - Mantener una única conexión a ChromaDB (singleton via
      lru_cache) para eliminar el overhead de reconexión en
      cada petición.
    - Recuperar los fragmentos más relevantes del corpus según
      la pregunta del usuario (búsqueda vectorial).
    - Construir el prompt final enriquecido con el contexto
      recuperado para reducir alucinaciones y mejorar la
      precisión de las respuestas.

  Uso desde main.py:
      from rag_engine import retrieve_context, build_rag_prompt
      contexto, fuentes = retrieve_context(pregunta)
      prompt = build_rag_prompt(pregunta, contexto)
==============================================================
"""

import logging
from functools import lru_cache
from pathlib import Path

import chromadb

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# Ruta al directorio con los datos de ChromaDB (relativa a este archivo)
CHROMA_DB_PATH = Path(__file__).parent / "datalake" / "artifacts" / "chroma_db"
COLLECTION_NAME = "convozpropia"

# Número de fragmentos a recuperar por consulta
# 3 es el equilibrio óptimo: suficiente contexto, mínima latencia
N_RESULTS = 3


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
                "El chatbot funcionará sin contexto RAG."
            )
            return None

        client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
        collection = client.get_collection(name=COLLECTION_NAME)
        total = collection.count()
        logger.info(f"[RAG] ChromaDB listo — colección '{COLLECTION_NAME}' con {total} chunks indexados.")
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

    Proceso:
      1. Obtiene la colección en memoria (singleton, sin overhead).
      2. Ejecuta la búsqueda vectorial por similitud semántica.
      3. Formatea los fragmentos recuperados como contexto legible.

    Args:
        pregunta  : Consulta del usuario.
        n_results : Número de fragmentos a recuperar (default: 3).

    Returns:
        (contexto_formateado, lista_de_fuentes)
        Si ChromaDB no está disponible, devuelve ("", []) para
        modo degradado: el chatbot sigue funcionando sin RAG.
    """
    collection = _get_collection()
    if collection is None:
        return "", []

    try:
        results = collection.query(
            query_texts=[pregunta],
            n_results=min(n_results, collection.count()),
        )

        docs = results.get("documents", [[]])[0]
        if not docs:
            logger.debug("[RAG] No se encontraron fragmentos relevantes para la consulta.")
            return "", []

        # Formatear fragmentos recuperados como bloque de contexto
        partes = []
        for i, doc in enumerate(docs, start=1):
            partes.append(f"[Fragmento {i}]:\n{doc.strip()}")

        contexto = "\n\n".join(partes)
        fuentes = [f"RAG:convozpropia:frag_{i}" for i in range(1, len(docs) + 1)]

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

    Si hay contexto disponible, instruye al modelo para que base
    su respuesta en los fragmentos recuperados, reduciendo las
    alucinaciones y acortando las respuestas (= menor latencia).

    Si no hay contexto, devuelve la pregunta sin modificar para
    que el modelo responda con su conocimiento base.

    Args:
        pregunta : Consulta original del usuario.
        contexto : Fragmentos recuperados de ChromaDB.

    Returns:
        Prompt listo para enviar al modelo LLM.
    """
    if contexto:
        return (
            "Eres un asistente experto en el Plan Lector del centro educativo. "
            "Responde ÚNICAMENTE basándote en la siguiente información del corpus. "
            "Si la información no es suficiente, indícalo brevemente.\n\n"
            f"=== INFORMACIÓN DEL PLAN LECTOR ===\n{contexto}\n"
            "=== FIN DE LA INFORMACIÓN ===\n\n"
            f"Pregunta del alumno: {pregunta}\n\n"
            "Respuesta (concisa y directa):"
        )

    # Degraded mode: sin contexto RAG
    return (
        "Eres un asistente experto en el Plan Lector del centro educativo. "
        "Ayudas a los alumnos con dudas sobre libros y lecturas.\n\n"
        f"Pregunta: {pregunta}\n\nRespuesta:"
    )


# ---------------------------------------------------------------------------
# Utilidad: warm-up al importar
# ---------------------------------------------------------------------------

def warmup():
    """
    Precarga la conexión a ChromaDB al arrancar la aplicación.
    Llámala desde main.py al inicializar la app para eliminar
    la latencia del primer request (~200-400ms).
    """
    logger.info("[RAG] Iniciando warm-up de ChromaDB...")
    _get_collection()
    logger.info("[RAG] Warm-up completado.")
