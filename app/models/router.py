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

@router.get("/default")
async def get_default_model(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """Retorna el modelo configurado por defecto por el administrador."""
    result = await db.execute(
        select(Config).where(Config.key == "default_model")
    )
    config = result.scalar_one_or_none()
    if not config or not config.value:
        # Fallback: retorna el primero disponible en Ollama
        available = await fetch_available_models()
        return {"default_model": available[0] if available else None}
    return {"default_model": config.value}