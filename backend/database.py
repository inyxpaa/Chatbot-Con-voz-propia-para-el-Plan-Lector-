from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, Float
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
import os

# PostgreSQL via env var (DATABASE_URL), fallback a SQLite para desarrollo local
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{os.path.join(BASE_DIR, 'chatbot_plan_lector.db')}"
)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class Busqueda(Base):
    """Registro completo de cada búsqueda/consulta al chatbot."""
    __tablename__ = "busquedas"

    id                  = Column(Integer, primary_key=True, index=True)
    session_id          = Column(String(64), index=True, nullable=True)
    pregunta            = Column(Text, nullable=False)
    respuesta           = Column(Text, nullable=True)
    fuentes             = Column(Text, nullable=True)           # JSON: ["chroma:quijote"]
    bloqueada           = Column(Boolean, default=False)        # True si el filtro la rechazó
    categoria_bloqueo   = Column(String(64), nullable=True)     # "insulto", "odio", etc.
    tiempo_respuesta_ms = Column(Float, nullable=True)          # milisegundos
    creada_en           = Column(DateTime, default=datetime.datetime.utcnow, index=True)


# Tabla legacy — se conserva para no romper migraciones anteriores
class Interaction(Base):
    __tablename__ = "interactions"

    id         = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True, nullable=True)
    question   = Column(String)
    answer     = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


def create_tables():
    Base.metadata.create_all(bind=engine)