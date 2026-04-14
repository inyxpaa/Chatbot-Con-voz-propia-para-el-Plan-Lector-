from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

SQLALCHEMY_DATABASE_URL = "postgresql://postgres:1234@localhost:5432/chatbot_db"

engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# --- MODELOS ---
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Interaction(Base):
    __tablename__ = "interactions"
    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, index=True, nullable=True)
    question = Column(String)
    answer = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class RedFlag(Base):
    __tablename__ = "red_flags"
    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, index=True)
    content = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

def create_tables():
    Base.metadata.create_all(bind=engine)