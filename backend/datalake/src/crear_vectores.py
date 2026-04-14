import chromadb
from pathlib import Path
import os
import sys

base_dir = Path(__file__).resolve().parent.parent / "datalake"
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