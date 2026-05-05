from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.db.database import get_db
from app.db.models import Config, User
from app.middleware.auth import require_admin

router = APIRouter(prefix="/admin", tags=["admin"])

class SystemPromptUpdate(BaseModel):
    value: str

class SystemPromptResponse(BaseModel):
    key: str
    value: str

@router.get("/config", response_model=SystemPromptResponse)
async def get_config(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin)
):
    result = await db.execute(
        select(Config).where(Config.key == "system_prompt")
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Configuración no encontrada.")
    return SystemPromptResponse(key=config.key, value=config.value)

@router.put("/config", response_model=SystemPromptResponse)
async def update_config(
    body: SystemPromptUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin)
):
    result = await db.execute(
        select(Config).where(Config.key == "system_prompt")
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Configuración no encontrada.")

    config.value = body.value
    await db.commit()
    await db.refresh(config)
    return SystemPromptResponse(key=config.key, value=config.value)

@router.get("/users")
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin)
):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return [{"id": u.id, "username": u.username, "email": u.email, "role": u.role} for u in users]

@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    role: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin)
):
    if role not in ("user", "admin"):
        raise HTTPException(status_code=400, detail="Rol inválido. Use 'user' o 'admin'.")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    user.role = role
    await db.commit()
    return {"id": user.id, "username": user.username, "email": user.email, "role": user.role}