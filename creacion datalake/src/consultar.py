import chromadb
from pathlib import Path
import os
import sys

# Cambiamos el directorio de trabajo al del script para evitar bugs de ChromaDB con rutas absolutas que contienen Ñ/acentos.
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

base_dir = Path("datalake")
db_path = base_dir / "artifacts" / "chroma_db"

cliente = chromadb.PersistentClient(path=str(db_path))
coleccion = cliente.get_collection(name="quijote")

pregunta = "¿Quién es Sancho Panza?"

resultados = coleccion.query(
    query_texts=[pregunta],
    n_results=2
)

print(resultados["documents"][0])