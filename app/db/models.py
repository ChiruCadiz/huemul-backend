from sqlalchemy import Column, Integer, String, Text, DateTime, func
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