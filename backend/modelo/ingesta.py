"""
==============================================================
  ingesta.py — Pipeline de Ingestión y Creación del Índice
==============================================================
  Proyecto : Chatbot Plan Lector (RAG)
  Autor    : Equipo de Desarrollo
  Uso      : python modelo/ingesta.py   (desde backend/)

  Qué hace este script:
    1. Lee documentos del Data Lake (capa RAW)
       Formatos soportados: .txt  .md  .pdf  .epub
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
# CONFIGURACIÓN
# ------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Data Lake RAW — misma ruta del repositorio (renombrada tras el pull)
DATA_LAKE_DIR = os.path.join(BASE_DIR, "datalake", "raw")

# Salida del índice vectorial
DB_DIR     = os.path.join(BASE_DIR, "data", "db")
INDEX_FILE = os.path.join(DB_DIR, "index.faiss")
META_FILE  = os.path.join(DB_DIR, "metadata.json")

# Modelo de embeddings multilingüe
# Dim: 384 | Tamaño: ~470 MB | Velocidad: rápida en CPU
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

# Parámetros de chunking
# 250 chars maximiza relevancia (scores ~0.55+) sin perder contexto
CHUNK_SIZE    = 250
CHUNK_OVERLAP = 50

# Formatos de documento aceptados por el pipeline
FORMATOS_SOPORTADOS = {".txt", ".md", ".pdf", ".epub"}
# ------------------------------------------------------------------


# ------------------------------------------------------------------
# CARGA DE DOCUMENTOS — multi-formato
# ------------------------------------------------------------------
def _leer_txt(ruta: str) -> str:
    """Lee un archivo de texto plano o Markdown."""
    with open(ruta, "r", encoding="utf-8", errors="replace") as f:
        return f.read().strip()


def _leer_pdf(ruta: str) -> str:
    """
    Extrae texto de un PDF página a página.
    Requiere: pip install pypdf2   (ya incluido en requirements.txt)
    """
    try:
        import PyPDF2
        texto = []
        with open(ruta, "rb") as f:
            lector = PyPDF2.PdfReader(f)
            for pagina in lector.pages:
                contenido = pagina.extract_text()
                if contenido:
                    texto.append(contenido.strip())
        return "\n\n".join(texto)
    except ImportError:
        print("   [AVISO] PyPDF2 no instalado. Omitiendo PDF:", ruta)
        return ""
    except Exception as e:
        print(f"   [ERROR] No se pudo leer el PDF '{ruta}': {e}")
        return ""


def _leer_epub(ruta: str) -> str:
    """
    Extrae texto de un EPUB capítulo a capítulo.
    Requiere: pip install ebooklib beautifulsoup4
    """
    try:
        import ebooklib
        from ebooklib import epub
        from bs4 import BeautifulSoup

        libro = epub.read_epub(ruta)
        partes = []
        for item in libro.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            soup = BeautifulSoup(item.get_content(), "html.parser")
            texto = soup.get_text(separator="\n").strip()
            if texto:
                partes.append(texto)
        return "\n\n".join(partes)
    except ImportError:
        print("   [AVISO] ebooklib/beautifulsoup4 no instalados. Omitiendo EPUB:", ruta)
        return ""
    except Exception as e:
        print(f"   [ERROR] No se pudo leer el EPUB '{ruta}': {e}")
        return ""


LECTORES = {
    ".txt" : _leer_txt,
    ".md"  : _leer_txt,   # Markdown se trata como texto plano
    ".pdf" : _leer_pdf,
    ".epub": _leer_epub,
}


def cargar_documentos_datalake(datalake_raw_dir: str) -> list[dict]:
    """
    Lee todos los documentos soportados de la capa RAW del Data Lake.

    El Data Lake actúa como fuente de verdad para el corpus del Plan
    Lector. Se aceptan .txt, .md, .pdf y .epub. Los archivos con
    extensiones no soportadas se ignoran con aviso.

    Args:
        datalake_raw_dir : Ruta a la carpeta raw/ del Data Lake.

    Returns:
        Lista de dicts con keys: 'filename', 'extension', 'text'
    """
    documentos = []

    if not os.path.isdir(datalake_raw_dir):
        print(f"[ERROR] Directorio del Data Lake no encontrado: '{datalake_raw_dir}'")
        print("        Comprueba que el datalake está en backend/datalake/datalake/raw/")
        return []

    archivos = sorted(os.listdir(datalake_raw_dir))
    if not archivos:
        print(f"[AVISO] El Data Lake raw/ está vacío: '{datalake_raw_dir}'")
        return []

    print(f"[Data Lake] Archivos encontrados en raw/: {len(archivos)}")

    for nombre in archivos:
        ext = os.path.splitext(nombre)[1].lower()

        if ext not in FORMATOS_SOPORTADOS:
            print(f"   [SKIP] Formato no soportado: {nombre}")
            continue

        ruta = os.path.join(datalake_raw_dir, nombre)
        lector = LECTORES[ext]
        texto = lector(ruta)

        if texto:
            documentos.append({
                "filename" : nombre,
                "extension": ext,
                "text"     : texto
            })
            print(f"   [OK] {nombre} ({ext}) — {len(texto):,} caracteres")
        else:
            print(f"   [VACÍO] {nombre} no produjo texto, se omite.")

    return documentos


# ------------------------------------------------------------------
# CHUNKING
# ------------------------------------------------------------------
def dividir_en_chunks(texto: str, fuente: str,
                      chunk_size: int = CHUNK_SIZE,
                      overlap: int = CHUNK_OVERLAP) -> list[dict]:
    """
    Divide un texto largo en fragmentos de tamaño fijo con solape.

    El solape garantiza que el contexto no se corte abruptamente en
    los bordes de cada chunk.

    Args:
        texto      : Texto completo del documento.
        fuente     : Nombre del archivo origen (para metadatos).
        chunk_size : Número de caracteres por chunk.
        overlap    : Caracteres de solape entre chunks consecutivos.

    Returns:
        Lista de dicts con keys: 'chunk_id', 'source', 'text', 'start_char'
    """
    chunks = []
    inicio = 0
    idx = 0

    while inicio < len(texto):
        fin = inicio + chunk_size
        fragmento = texto[inicio:fin].strip()

        if fragmento:
            chunks.append({
                "chunk_id"  : f"{fuente}__{idx:04d}",
                "source"    : fuente,
                "text"      : fragmento,
                "start_char": inicio
            })
            idx += 1

        inicio = fin - overlap   # Solape con el chunk anterior

    return chunks


# ------------------------------------------------------------------
# EMBEDDINGS
# ------------------------------------------------------------------
def generar_embeddings(chunks: list[dict], modelo: SentenceTransformer) -> np.ndarray:
    """
    Convierte la lista de chunks a una matriz de embeddings normalizados.

    Returns:
        numpy array de forma (num_chunks, dimensión_embedding)
    """
    textos = [c["text"] for c in chunks]
    print(f"\n[Embeddings] Generando para {len(textos)} chunks...")

    embeddings = modelo.encode(
        textos,
        batch_size=32,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True   # Normalizar => coseno ≡ producto interno
    )
    return embeddings


# ------------------------------------------------------------------
# ÍNDICE FAISS
# ------------------------------------------------------------------
def construir_y_guardar_indice(embeddings: np.ndarray, chunks: list[dict]) -> None:
    """
    Construye el índice FAISS IndexFlatIP y lo persiste junto a los metadatos.

    IndexFlatIP (Inner Product) equivale a similitud coseno cuando los
    vectores están normalizados, lo que maximiza la precisión de búsqueda.
    """
    os.makedirs(DB_DIR, exist_ok=True)

    dimension = embeddings.shape[1]
    print(f"\n[FAISS] Construyendo índice (dim={dimension}, vectores={len(embeddings)})...")

    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings.astype(np.float32))

    faiss.write_index(index, INDEX_FILE)
    print(f"   - Índice guardado en: {INDEX_FILE}")

    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    print(f"   - Metadatos guardados en: {META_FILE}")


# ------------------------------------------------------------------
# PUNTO DE ENTRADA
# ------------------------------------------------------------------
def main():
    print("=" * 60)
    print("  PIPELINE DE INGESTION — PLAN LECTOR RAG")
    print("=" * 60)
    print(f"  Fuente : {DATA_LAKE_DIR}")
    print(f"  Salida : {DB_DIR}")
    print(f"  Formatos aceptados: {', '.join(sorted(FORMATOS_SOPORTADOS))}")
    print("=" * 60)

    # 1. Cargar documentos desde el Data Lake
    documentos = cargar_documentos_datalake(DATA_LAKE_DIR)
    if not documentos:
        print("\n[ABORT] No hay documentos que procesar.")
        return

    # 2. Dividir en chunks
    print("\nDividiendo documentos en fragmentos...")
    todos_los_chunks = []
    for doc in tqdm(documentos, desc="Chunking"):
        chunks = dividir_en_chunks(doc["text"], doc["filename"])
        todos_los_chunks.extend(chunks)

    print(f"   → Total chunks generados: {len(todos_los_chunks)}")

    # 3. Cargar modelo de embeddings
    print(f"\n[Modelo] Cargando: {MODEL_NAME}")
    print("   (Primera vez tarda ~1-2 min mientras se descarga el modelo)")
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


if __name__ == "__main__":
    main()
