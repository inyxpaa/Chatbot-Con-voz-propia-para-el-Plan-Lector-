import chromadb
from pathlib import Path

base_dir = Path(__file__).resolve().parent.parent
processed_file = base_dir / "processed" / "convozpropia_chunks.txt"
db_path = base_dir / "artifacts" / "chroma_db"

def crear_vectores():
    if not processed_file.exists():
        print(f"No se encontró {processed_file}. Ejecuta procesar_texto.py primero.")
        return

    with open(processed_file, "r", encoding="utf-8") as f:
        texto = f.read()

    # Separar por nuestro delimitador configurado
    fragmentos = [t.strip() for t in texto.split("\n---\n") if t.strip()]

    print(f"Indexando {len(fragmentos)} fragmentos en ChromaDB...")

    # Inicializar ChromaDB (Persistente)
    cliente = chromadb.PersistentClient(path=str(db_path))

    # Usaremos una nueva colección para este proyecto
    mbre_coleccion = "convozpropia"
    print(f"Obteniendo o creando colección: {mbre_coleccion}")
    
    # Intentar obtener la colección o crearla
    # Eliminamos toda la info antigua para recrearla desde 0 y no tener duplicados
    try:
        cliente.delete_collection(name=mbre_coleccion)
        print("Colección antigua eliminada.")
    except BaseException:
        pass # La colección no existía

    coleccion = cliente.create_collection(name=mbre_coleccion)

    # Generar ids para los documentos
    ids = [str(i) for i in range(len(fragmentos))]

    # Agregar documentos a la colección (ChromaDB genera embeddings internamente con el modelo por defecto)
    coleccion.add(
        documents=fragmentos,
        ids=ids
    )

    print("Indexación completada con éxito.")

if __name__ == "__main__":
    crear_vectores()