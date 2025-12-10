from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "brainstorm.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

Base = declarative_base()

class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True)  # UUID string
    topic = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    current_phase = Column(String, default="intro")
    
    agents = relationship("Agent", back_populates="session", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")

class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.id"))
    name = Column(String)
    role = Column(String)
    model = Column(String, nullable=True)
    
    session = relationship("Session", back_populates="agents")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.id"))
    sender = Column(String)
    content = Column(Text)
    type = Column(String) # 'human', 'agent', 'facilitator', 'phase', 'summary'
    timestamp = Column(DateTime, default=datetime.now)
    phase = Column(String, nullable=True)
    role = Column(String, nullable=True)
    model = Column(String, nullable=True)
    
    session = relationship("Session", back_populates="messages")

# Setup Database
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
