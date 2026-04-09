from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

# Definimos la ubicación de la DB local [cite: 67]
SQLALCHEMY_DATABASE_URL = "sqlite:///./src/backend/chatbot_plan_lector.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Modelo para registrar interacciones (Issue #21 y #48) [cite: 11, 48]
class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(String)
    answer = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

def create_tables():
    Base.metadata.create_all(bind=engine)