from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.db.models import Config, User
from app.middleware.auth import get_current_user
from app.models.service import fetch_available_models

router = APIRouter(prefix="/models", tags=["models"])

@router.get("")
async def list_models(_: User = Depends(get_current_user)):
    """Retorna lista de modelos disponibles en Ollama."""
    models = await fetch_available_models()
    if not models:
        return {
            "models": [],
            "message": "No hay modelos disponibles. Contacte al administrador."
        }
    return {"models": models}