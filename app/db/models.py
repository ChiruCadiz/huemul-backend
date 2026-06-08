import uuid
from sqlalchemy import (
    Column, Integer, String, Boolean,
    Text, DateTime, ForeignKey, func
)
from sqlalchemy.dialects.postgresql import UUID
from app.db.database import Base

class User(Base):
    __tablename__ = "users"

    id         = Column(Integer, primary_key=True, index=True)
    username   = Column(String(100), unique=True, nullable=False, index=True)
    email      = Column(String(255), unique=True, nullable=False)
    role       = Column(String(20), nullable=False, default="user")
    created_at = Column(DateTime, server_default=func.now())

class Config(Base):
    __tablename__ = "config"

    id    = Column(Integer, primary_key=True)
    key   = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=True)

class Session(Base):
    __tablename__ = "sessions"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id        = Column(Integer, ForeignKey("users.id"), nullable=False)
    title          = Column(String(255), nullable=True)
    model_used     = Column(String(100), nullable=False, default="codellama")
    is_active      = Column(Boolean, default=True, nullable=False)
    created_at     = Column(DateTime, server_default=func.now())
    last_active_at = Column(DateTime, server_default=func.now())

class Message(Base):
    __tablename__ = "messages"

    id         = Column(Integer, primary_key=True, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    role       = Column(String(20), nullable=False)  # "user" | "assistant"
    content    = Column(Text, nullable=False)
    timestamp  = Column(DateTime, server_default=func.now())