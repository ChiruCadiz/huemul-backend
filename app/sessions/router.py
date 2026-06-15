from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func as sqlfunc
from pydantic import BaseModel
from loguru import logger
import uuid
from app.db.database import get_db
from app.db.models import Session, Message, User
from app.middleware.auth import get_current_user
from app.sessions.service import (
    create_session,
    persist_messages,
    load_history,
    list_sessions,
    get_session_detail,
    delete_session,
    generate_session_title,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])

class CreateSessionRequest(BaseModel):
    model: str = "gemma4:26b"

class SessionResponse(BaseModel):
    id: str
    title: str | None
    model_used: str
    is_active: bool
    created_at: str
    last_active_at: str

@router.post("", response_model=SessionResponse)
async def post_session(
    body: CreateSessionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await create_session(
        user_id=current_user.id,
        model=body.model,
        db=db
    )
    return SessionResponse(
        id=str(session.id),
        title=session.title,
        model_used=session.model_used,
        is_active=session.is_active,
        created_at=str(session.created_at),
        last_active_at=str(session.last_active_at),
    )

@router.get("", response_model=list[SessionResponse])
async def get_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sessions = await list_sessions(current_user.id, db)
    return [
        SessionResponse(
            id=str(s.id),
            title=s.title,
            model_used=s.model_used,
            is_active=s.is_active,
            created_at=str(s.created_at),
            last_active_at=str(s.last_active_at),
        )
        for s in sessions
    ]

@router.get("/{session_id}")
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session, history = await get_session_detail(
        session_id, current_user.id, db
    )
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada.")
    return {
        "id": str(session.id),
        "title": session.title,
        "model_used": session.model_used,
        "created_at": str(session.created_at),
        "last_active_at": str(session.last_active_at),
        "messages": history,
    }

@router.delete("/{session_id}")
async def delete_session_endpoint(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deleted = await delete_session(session_id, current_user.id, db)
    if not deleted:
        raise HTTPException(status_code=404, detail="Sesión no encontrada.")
    return {
        "message": "Sesión eliminada correctamente.",
        "session_id": session_id
    }