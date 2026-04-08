from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from .database import SessionLocal, create_tables, Interaction

# Inicializamos las tablas (Issue #20) [cite: 206]
create_tables()

app = FastAPI(title="Chatbot 'Con voz propia' API")

# Modelo de datos para validar la entrada (Issue #18) [cite: 33]
class ChatQuery(BaseModel):
    message: str

# Dependencia para la DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"message": "API del Plan Lector operativa"}

@app.post("/chat")
async def chat_endpoint(query: ChatQuery, db: Session = Depends(get_db)):
    # Por ahora es un mock, en el Sprint 2 conectaremos el RAG [cite: 223, 235]
    user_text = query.message
    bot_response = f"Has preguntado sobre: {user_text}. El motor RAG está en fase de diseño."

    # Guardamos la interacción para métricas (Issue #21 / #36) [cite: 36, 48, 116]
    new_log = Interaction(question=user_text, answer=bot_response)
    db.add(new_log)
    db.commit()

    return {"response": bot_response, "sources": []}