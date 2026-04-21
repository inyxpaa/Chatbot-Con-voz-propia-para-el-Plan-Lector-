from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, Float
from sqlalchemy.orm import declarative_base, sessionmaker
import datetime
import os

# ---------------------------------------------------------------------------
# URL de la base de datos
# ---------------------------------------------------------------------------
# En AWS se debe establecer via variable de entorno:
#   DATABASE_URL=postgresql://usuario:password@host:5432/nombre_db
#
# En local (desarrollo) cae al SQLite embebido.

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{os.path.join(BASE_DIR, 'chatbot_plan_lector.db')}"
)

# ---------------------------------------------------------------------------
# Configuración del engine según el tipo de BD
# ---------------------------------------------------------------------------
is_sqlite = DATABASE_URL.startswith("sqlite")

if is_sqlite:
    # SQLite: solo para desarrollo local, no soporta concurrencia real
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    # PostgreSQL en AWS: pool robusto con reconexión automática
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,          # conexiones permanentes en el pool
        max_overflow=20,       # conexiones extra bajo picos de tráfico
        pool_pre_ping=True,    # verifica conexiones antes de usarlas (evita "gone away")
        pool_recycle=1800,     # recicla conexiones cada 30 min (AWS RDS cierra a los 60)
        connect_args={
            "connect_timeout": 10,         # timeout de conexión inicial
            "application_name": "chatbot-plan-lector",  # visible en pg_stat_activity
        },
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base         = declarative_base()


# ---------------------------------------------------------------------------
# Modelos ORM
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id         = Column(Integer, primary_key=True, index=True)
    email      = Column(String(128), unique=True, index=True, nullable=False)
    name       = Column(String(128), nullable=True)
    picture    = Column(String(256), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Busqueda(Base):
    """Registro completo de cada búsqueda/consulta al chatbot."""
    __tablename__ = "busquedas"

    id                  = Column(Integer, primary_key=True, index=True)
    user_email          = Column(String(128), index=True, nullable=True)  # SHA-256 (Tarea 1)
    session_id          = Column(String(64),  index=True, nullable=True)
    pregunta            = Column(Text, nullable=False)
    respuesta           = Column(Text, nullable=True)
    fuentes             = Column(Text, nullable=True)           # JSON list
    bloqueada           = Column(Boolean, default=False)        # True si filtro rechazó
    categoria_bloqueo   = Column(String(64), nullable=True)     # "insultos", "odio", etc.
    tiempo_respuesta_ms = Column(Float, nullable=True)          # ms total del request
    creada_en           = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class Interaction(Base):
    """Tabla legacy — conservada para no romper migraciones anteriores."""
    __tablename__ = "interactions"

    id         = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True, nullable=True)
    question   = Column(String)
    answer     = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


# ---------------------------------------------------------------------------

def create_tables():
    Base.metadata.create_all(bind=engine)