import chromadb
from pathlib import Path
import os
import sys

# Cambiamos el directorio de trabajo al del script para evitar bugs de ChromaDB con rutas absolutas que contienen Ñ/acentos.
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

base_dir = Path("datalake")
processed_file = base_dir / "processed" / "quijote_chunks.txt"
db_path = base_dir / "artifacts" / "chroma_db"

with open(processed_file, "r", encoding="utf-8") as f:
    texto = f.read()

fragmentos = [t.strip() for t in texto.split("\n---\n") if t.strip()]

cliente = chromadb.PersistentClient(path=str(db_path))
coleccion = cliente.get_or_create_collection(name="quijote")

ids = [str(i) for i in range(len(fragmentos))]

coleccion.add(
    documents=fragmentos,
    ids=ids
)