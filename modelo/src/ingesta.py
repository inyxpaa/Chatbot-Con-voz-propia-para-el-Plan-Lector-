"""
==============================================================
  ingesta.py — Pipeline de Ingestión y Creación del Índice
==============================================================
  Proyecto : Chatbot Plan Lector (RAG)
  Autor    : Equipo de Desarrollo
  Uso      : python src/ingesta.py   (desde la raíz del proyecto)

  Qué hace este script:
    1. Lee todos los archivos .txt de la capa RAW del Data Lake
    2. Divide cada documento en fragmentos (chunks) con solape
    3. Convierte cada chunk a un vector de embeddings
    4. Construye un índice FAISS y lo guarda en /data/db
==============================================================
"""

import os
import json
import numpy as np
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
import faiss

# ------------------------------------------------------------------
# CONFIGURACIÓN — Ajusta estos valores según tus necesidades
# ------------------------------------------------------------------
# Rutas relativas a la RAÍZ del proyecto (ejecutar desde ProyectoFinal/)
BASE_DIR     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Data Lake: capa RAW donde se almacenan los documentos originales del Plan Lector
DATA_LAKE_DIR = os.path.join(BASE_DIR, "creacion datalake", "datalake", "raw")

# Directorio de salida del índice vectorial (no cambia)
DATA_DIR     = os.path.join(BASE_DIR, "data")
DB_DIR       = os.path.join(DATA_DIR, "db")            # Carpeta donde se guarda el índice
INDEX_FILE   = os.path.join(DB_DIR, "index.faiss")
META_FILE    = os.path.join(DB_DIR, "metadata.json")

# Modelo de embeddings multilingüe (excelente en español, ligero en CPU)
# Dimensión de salida: 384  |  Tamaño: ~470 MB  |  Velocidad: rápida en CPU
MODEL_NAME   = "paraphrase-multilingual-MiniLM-L12-v2"

# Parámetros de chunking
# Fragmentos cortos mejoran la precision del embedding y elevan los scores de relevancia.
# Referencia: con 500 chars los scores eran ~0.35; con 250 se espera superar 0.55.
CHUNK_SIZE    = 250   # Caracteres por fragmento  (antes: 500)
CHUNK_OVERLAP = 50    # Solape entre fragmentos    (antes: 100)
# ------------------------------------------------------------------


def cargar_documentos_datalake(datalake_raw_dir: str) -> list[dict]:
    """
    Lee todos los archivos .txt de la capa RAW del Data Lake.

    El Data Lake actúa como fuente de verdad para los documentos
    del Plan Lector. La capa 'raw' contiene los textos originales
    sin procesar, que serán fragmentados por este pipeline.

    Args:
        datalake_raw_dir : Ruta a la capa raw/ del Data Lake.

    Returns:
        Lista de dicts con keys: 'filename', 'text'
    """
    documentos = []

    if not os.path.isdir(datalake_raw_dir):
        print(f"[ERROR] No se encontró el directorio del Data Lake: '{datalake_raw_dir}'.")
        print("        Asegúrate de ejecutar el script desde la raíz del proyecto.")
        return []

    archivos = [f for f in os.listdir(datalake_raw_dir) if f.endswith(".txt")]

    if not archivos:
        print(f"[AVISO] No se encontraron archivos .txt en el Data Lake ('{datalake_raw_dir}').")
        return []

    print(f"[Data Lake] Documentos encontrados en raw/: {len(archivos)}")
    for nombre in sorted(archivos):
        ruta = os.path.join(datalake_raw_dir, nombre)
        with open(ruta, "r", encoding="utf-8") as f:
            texto = f.read().strip()
        if texto:
            documentos.append({"filename": nombre, "text": texto})
            print(f"   - {nombre} ({len(texto):,} caracteres)")

    return documentos


def dividir_en_chunks(texto: str, fuente: str,
                      chunk_size: int = CHUNK_SIZE,
                      overlap: int = CHUNK_OVERLAP) -> list[dict]:
    """
    Divide un texto largo en fragmentos de tamaño fijo con solape.
    El solape garantiza que el contexto no se corte abruptamente.

    Args:
        texto      : Texto completo del documento.
        fuente     : Nombre del archivo origen (para metadatos).
        chunk_size : Número de caracteres por chunk.
        overlap    : Caracteres de solape entre chunks.

    Returns:
        Lista de dicts con keys: 'chunk_id', 'source', 'text', 'start_char'
    """
    chunks = []
    inicio = 0
    idx = 0

    while inicio < len(texto):
        fin = inicio + chunk_size
        fragmento = texto[inicio:fin].strip()

        if fragmento:  # Ignora fragmentos vacíos
            chunks.append({
                "chunk_id"  : f"{fuente}__{idx:04d}",
                "source"    : fuente,
                "text"      : fragmento,
                "start_char": inicio
            })
            idx += 1

        # Avanza con solape: el siguiente chunk empieza antes de donde acabó éste
        inicio = fin - overlap

    return chunks


def generar_embeddings(chunks: list[dict], modelo: SentenceTransformer) -> np.ndarray:
    """
    Convierte la lista de chunks a una matriz de embeddings.

    Returns:
        numpy array de forma (num_chunks, dimensión_embedding)
    """
    textos = [c["text"] for c in chunks]
    print(f"\nGenerando embeddings para {len(textos)} chunks...")

    embeddings = modelo.encode(
        textos,
        batch_size=32,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True  # Normalizar facilita la búsqueda por coseno
    )
    return embeddings


def construir_y_guardar_indice(embeddings: np.ndarray,
                               chunks: list[dict]) -> None:
    """
    Construye el índice FAISS y lo persiste junto a los metadatos.

    Usamos IndexFlatIP (Inner Product) porque los embeddings están
    normalizados, lo que equivale a similitud de coseno.
    """
    os.makedirs(DB_DIR, exist_ok=True)

    dimension = embeddings.shape[1]
    print(f"\nConstruyendo indice FAISS (dim={dimension}, vectores={len(embeddings)})...")

    # Índice de producto interno (≡ coseno para vectores normalizados)
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings.astype(np.float32))

    # Guardar el índice binario
    faiss.write_index(index, INDEX_FILE)
    print(f"   - Indice guardado en: {INDEX_FILE}")

    # Guardar los metadatos (texto + fuente de cada chunk)
    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    print(f"   - Metadatos guardados en: {META_FILE}")


def main():
    print("=" * 60)
    print("  PIPELINE DE INGESTION -- PLAN LECTOR RAG")
    print("=" * 60)
    print(f"  Fuente : Data Lake → {DATA_LAKE_DIR}")
    print(f"  Salida : {DB_DIR}")
    print("=" * 60)

    # 1. Cargar documentos desde la capa RAW del Data Lake
    documentos = cargar_documentos_datalake(DATA_LAKE_DIR)
    if not documentos:
        return

    # 2. Dividir en chunks
    print("\nDividiendo documentos en fragmentos...")
    todos_los_chunks = []
    for doc in tqdm(documentos, desc="Chunking"):
        chunks = dividir_en_chunks(doc["text"], doc["filename"])
        todos_los_chunks.extend(chunks)

    print(f"   → Total de chunks generados: {len(todos_los_chunks)}")

    # 3. Cargar modelo de embeddings
    print(f"\nCargando modelo de embeddings: {MODEL_NAME}")
    print("   (Primera vez tarda ~1-2 min mientras descarga el modelo)")
    modelo = SentenceTransformer(MODEL_NAME)

    # 4. Generar embeddings
    embeddings = generar_embeddings(todos_los_chunks, modelo)

    # 5. Construir y guardar índice FAISS
    construir_y_guardar_indice(embeddings, todos_los_chunks)

    print("\n" + "=" * 60)
    print("  INGESTION COMPLETADA")
    print(f"     Documentos procesados : {len(documentos)}")
    print(f"     Chunks indexados      : {len(todos_los_chunks)}")
    print(f"     Dimension embeddings  : {embeddings.shape[1]}")
    print("=" * 60)
    print("\nA continuacion ejecuta: python src/app.py")


if __name__ == "__main__":
    main()
