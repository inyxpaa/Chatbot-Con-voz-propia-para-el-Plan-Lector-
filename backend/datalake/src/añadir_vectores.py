import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import chromadb
from pathlib import Path

base_dir = Path(__file__).resolve().parent.parent
processed_file = base_dir / "processed" / "convozpropia_chunks.txt"
db_path = base_dir / "artifacts" / "chroma_db"
NOMBRE_COLECCION = "convozpropia"


def anadir_vectores():
    if not processed_file.exists():
        print(f"No se encontro {processed_file}.")
        return

    with open(processed_file, "r", encoding="utf-8") as f:
        texto = f.read()

    todos_los_fragmentos = [t.strip() for t in texto.split("\n---\n") if t.strip()]
    print(f"Total de chunks en fichero: {len(todos_los_fragmentos)}")

    cliente = chromadb.PersistentClient(path=str(db_path))
    coleccion = cliente.get_or_create_collection(name=NOMBRE_COLECCION)
    ya_indexados = coleccion.count()
    print(f"Chunks ya indexados en ChromaDB: {ya_indexados}")

    nuevos = todos_los_fragmentos[ya_indexados:]
    if not nuevos:
        print("No hay chunks nuevos que anadir. Todo esta actualizado.")
        return

    print(f"Anadiendo {len(nuevos)} chunks nuevos...")

    ids = [str(i) for i in range(ya_indexados, ya_indexados + len(nuevos))]

    LOTE = 500
    for i in range(0, len(nuevos), LOTE):
        lote_docs = nuevos[i: i + LOTE]
        lote_ids  = ids[i: i + LOTE]
        coleccion.add(documents=lote_docs, ids=lote_ids)
        print(f"  Lote {i // LOTE + 1}: {len(lote_docs)} fragmentos indexados")

    print(f"Indexacion completada. Total en coleccion: {coleccion.count()}")


if __name__ == "__main__":
    anadir_vectores()
