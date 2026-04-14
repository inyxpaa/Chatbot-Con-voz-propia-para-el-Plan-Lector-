"""
==============================================================
  app.py — Motor de Búsqueda RAG (sin interfaz propia)
==============================================================
  Proyecto : Chatbot Plan Lector (RAG)
  Autor    : Equipo de Desarrollo

  Qué hace este módulo:
    - Carga el índice FAISS generado por ingesta.py
    - Carga el modelo de embeddings
    - Filtra consultas inapropiadas (insultos, racismo, odio)
      antes de procesarlas mediante filtro.py
    - Expone la función `buscar()` para ser consumida
      directamente por el backend FastAPI (main.py)

  NO incluye ninguna interfaz gráfica propia: la UI la
  provee el frontend web del proyecto.
=============================================================="""

import os
import json
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss

from filtro import verificar_consulta, censurar_texto

# ------------------------------------------------------------------
# CONFIGURACIÓN — Debe coincidir con ingesta.py
# ------------------------------------------------------------------
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR     = os.path.join(BASE_DIR, "data", "db")
INDEX_FILE = os.path.join(DB_DIR, "index.faiss")
META_FILE  = os.path.join(DB_DIR, "metadata.json")
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
TOP_K      = 5   # Número de fragmentos a recuperar por defecto
# ------------------------------------------------------------------


# ------------------------------------------------------------------
# CARGA DE RECURSOS (se ejecuta una sola vez al arrancar el backend)
# ------------------------------------------------------------------
def cargar_recursos():
    """
    Carga el modelo de embeddings, el índice FAISS y los metadatos.

    Returns:
        Tupla (modelo, index, metadata) listos para consultar.

    Raises:
        FileNotFoundError: Si el índice no existe aún (falta ejecutar ingesta.py).
    """
    if not os.path.exists(INDEX_FILE):
        raise FileNotFoundError(
            f"No se encontró el índice en '{INDEX_FILE}'.\n"
            "Ejecuta primero: python modelo/ingesta.py"
        )

    print(f"[RAG] Cargando modelo de embeddings: {MODEL_NAME}...")
    modelo = SentenceTransformer(MODEL_NAME)

    print(f"[RAG] Cargando índice FAISS desde: {INDEX_FILE}")
    index = faiss.read_index(INDEX_FILE)

    print(f"[RAG] Cargando metadatos desde: {META_FILE}")
    with open(META_FILE, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    print(f"[RAG] Listo. Chunks indexados: {index.ntotal}")
    return modelo, index, metadata


# ------------------------------------------------------------------
# LÓGICA DE BÚSQUEDA — Función principal exportada al backend
# ------------------------------------------------------------------
def buscar(consulta: str, modelo, index, metadata, top_k: int = TOP_K) -> dict:
    """
    Filtra la consulta y, si es apropiada, recupera los chunks más similares.

    Diseñada para ser llamada desde main.py (FastAPI) de forma síncrona.
    Los recursos (modelo, index, metadata) se pasan como parámetros para
    evitar estado global y facilitar el testeo.

    Args:
        consulta  : Pregunta o texto libre del usuario.
        modelo    : Instancia de SentenceTransformer ya cargada.
        index     : Índice FAISS ya cargado.
        metadata  : Lista de dicts con metadatos de cada chunk.
        top_k     : Cuántos fragmentos retornar.

    Returns:
        {
            "aceptado"   : bool,
            "mensaje"    : str,        # Mensaje de error si fue rechazado
            "resultados" : list[dict]  # Vacío si fue rechazado
        }
    """
    if not consulta or not consulta.strip():
        return {"aceptado": False, "mensaje": "Consulta vacía.", "resultados": []}

    # ── Filtro de contenido inapropiado ──────────────────────────────
    verificacion = verificar_consulta(consulta)
    if not verificacion["aceptado"]:
        return {
            "aceptado"  : False,
            "mensaje"   : verificacion["mensaje"],
            "resultados": []
        }
    # ─────────────────────────────────────────────────────────────────

    # Convertir consulta a embedding normalizado
    query_vec = modelo.encode(
        [consulta.strip()],
        convert_to_numpy=True,
        normalize_embeddings=True
    ).astype(np.float32)

    # Buscar los top_k más similares en FAISS
    distancias, indices = index.search(query_vec, top_k)

    resultados = []
    for rank, (idx, score) in enumerate(zip(indices[0], distancias[0]), start=1):
        if idx == -1:   # FAISS devuelve -1 si no hay suficientes resultados
            continue
        chunk = metadata[idx]
        # Censurar también el texto recuperado del corpus por precaución
        texto_limpio = censurar_texto(chunk.get("text", ""))
        resultados.append({
            "rank"  : rank,
            "score" : round(float(score), 4),
            "source": chunk.get("source", "desconocido"),
            "text"  : texto_limpio
        })

    return {
        "aceptado"  : True,
        "mensaje"   : "",
        "resultados": resultados
    }
