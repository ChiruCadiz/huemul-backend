from sqlalchemy import Column, Integer, String, Text, DateTime, func
from app.db.database import Base

class User(Base):
    __tablename__ = "users"

    id         = Column(Integer, primary_key=True, index=True)
    username   = Column(String(100), unique=True, nullable=False, index=True)
    email      = Column(String(255), unique=True, nullable=False)
    role       = Column(String(20), nullable=False, default="user")  # "user" | "admin"
    created_at = Column(DateTime, server_default=func.now())