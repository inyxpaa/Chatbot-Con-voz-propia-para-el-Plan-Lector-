import chromadb

db_path = "backend/datalake/datalake/artifacts/chroma_db"
client = chromadb.PersistentClient(path=db_path)
collections = client.list_collections()
print("Collections found:")
for c in collections:
    print(f"  - Name: {c.name}, Count: {c.count()}")
