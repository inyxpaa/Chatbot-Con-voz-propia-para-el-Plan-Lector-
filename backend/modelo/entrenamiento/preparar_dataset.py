"""
==============================================================
  preparar_dataset.py — Preprocesamiento para Fine-Tuning Causal
==============================================================
  Lee todos los documentos del Data Lake y los convierte en un 
  dataset Parquet particionado, listo para ser consumido
  fluidamente por PySpark en el cluster.
==============================================================
"""

import os
import pandas as pd
from transformers import AutoTokenizer

# Directorio donde se guardará el dataset para PySpark
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(BASE_DIR, "data", "dataset_entrenamiento")
os.makedirs(DATASET_DIR, exist_ok=True)

DATA_LAKE_DIR = os.path.join(BASE_DIR, "datalake", "raw")

# Directorio donde se guardará el dataset para PySpark
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(BASE_DIR, "data", "dataset_entrenamiento")
os.makedirs(DATASET_DIR, exist_ok=True)

MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"
BLOCK_SIZE = 512  # Longitud máxima de secuencia para el entrenamiento

# --- LECTORES MULTI-FORMATO DEL DATALAKE ---
def _leer_txt(ruta: str) -> str:
    with open(ruta, "r", encoding="utf-8", errors="replace") as f: return f.read().strip()

def _leer_pdf(ruta: str) -> str:
    try:
        import PyPDF2
        texto = []
        with open(ruta, "rb") as f:
            for pagina in PyPDF2.PdfReader(f).pages:
                if c := pagina.extract_text(): texto.append(c.strip())
        return "\n\n".join(texto)
    except: return ""

def _leer_epub(ruta: str) -> str:
    try:
        import ebooklib
        from ebooklib import epub
        from bs4 import BeautifulSoup
        partes = []
        for item in epub.read_epub(ruta).get_items_of_type(ebooklib.ITEM_DOCUMENT):
            texto = BeautifulSoup(item.get_content(), "html.parser").get_text(separator="\n").strip()
            if texto: partes.append(texto)
        return "\n\n".join(partes)
    except: return ""

LECTORES = {".txt": _leer_txt, ".md": _leer_txt, ".pdf": _leer_pdf, ".epub": _leer_epub}

def cargar_documentos_datalake(datalake_raw_dir: str) -> list[dict]:
    documentos = []
    if not os.path.isdir(datalake_raw_dir): return []
    for nombre in sorted(os.listdir(datalake_raw_dir)):
        ext = os.path.splitext(nombre)[1].lower()
        if ext in LECTORES:
            texto = LECTORES[ext](os.path.join(datalake_raw_dir, nombre))
            if texto: documentos.append({"filename": nombre, "text": texto})
    return documentos
# -------------------------------------------

def main():
    print("=" * 60)
    print("  PREPARACIÓN DE DATASET PARA SPARK (Causal LM)")
    print("=" * 60)

    # 1. Cargar documentos crudos
    documentos = cargar_documentos_datalake(DATA_LAKE_DIR)
    if not documentos:
        print("[!] No se cargaron documentos. Revisa el Data Lake.")
        return

    # 2. Cargar tokenizador
    print(f"\nCargando tokenizador {MODEL_NAME}...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    
    # 3. Tokenizar todo el corpus y dividir en bloques de tamaño fijo
    bloques = []
    
    for doc in documentos:
        texto = doc["text"]
        if not texto: continue
        
        tokens = tokenizer.encode(texto, add_special_tokens=False)
        
        # Agrupar en trozos de BLOCK_SIZE
        for i in range(0, len(tokens) - BLOCK_SIZE + 1, BLOCK_SIZE):
            chunk = tokens[i : i + BLOCK_SIZE]
            
            # Para causal LM, input_ids == labels. HF se encarga de desplazar los labels internamente
            bloques.append({
                "source": doc["filename"],
                "input_ids": chunk,
            })
            
    if not bloques:
        print("[!] El corpus es demasiado pequeño para formar bloques.")
        return

    # 4. Convertir a Pandas y guardar a Parquet
    df = pd.DataFrame(bloques)
    # PyTorch y Petastorm prefieren que las listas sean arrays o strings, en Petastorm es usual guardarlos
    # pero guardándolo en Parquet normal, pyspark puede leer arreglos.
    
    ruta_parquet = os.path.join(DATASET_DIR, "dataset_chunks.parquet")
    df.to_parquet(ruta_parquet, engine="pyarrow", index=False)
    
    print("\n" + "=" * 60)
    print("  RESUMEN DEL DATASET")
    print("=" * 60)
    print(f"Documentos procesados : {len(documentos)}")
    print(f"Bloques generados     : {len(df)}")
    print(f"Ruta Parquet Spark    : {ruta_parquet}")
    print("El dataset está listo para usarse con PySpark/Horovod.")

if __name__ == "__main__":
    main()
