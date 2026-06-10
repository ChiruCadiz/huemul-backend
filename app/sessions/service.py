import uuid
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from app.db.models import Session, Message
from app.memory.session import get_session_history, clear_session, append_to_history

async def persist_messages(session_id: str, db: AsyncSession) -> None:
    """
    Guarda el historial activo de Redis → PostgreSQL.
    Evita duplicados verificando cuántos mensajes ya existen en BD.
    """
    history = await get_session_history(session_id)
    if not history:
        logger.debug(f"Sin mensajes que persistir para sesión {session_id}")
        return

    try:
        session_uuid = uuid.UUID(session_id)

        # Contar mensajes ya persistidos para evitar duplicados
        result = await db.execute(
            select(func.count()).where(Message.session_id == session_uuid)
        )
        existing_count = result.scalar()

        # Solo persistir mensajes nuevos
        new_messages = history[existing_count:]
        if not new_messages:
            return

        for msg in new_messages:
            db.add(Message(
                session_id=session_uuid,
                role=msg["role"],
                content=msg["content"]
            ))
        await db.commit()
        logger.info(
            f"Historial persistido — session: {session_id} | "
            f"mensajes nuevos: {len(new_messages)}"
        )
    except Exception as e:
        logger.error(f"Error al persistir mensajes de sesión {session_id}: {e}")
        await db.rollback()

async def load_history(session_id: str, db: AsyncSession) -> list[dict]:
    """
    Carga el historial desde PostgreSQL → Redis.
    Se llama al reabrir una sesión sin historial en Redis.
    """
    try:
        session_uuid = uuid.UUID(session_id)
        result = await db.execute(
            select(Message)
            .where(Message.session_id == session_uuid)
            .order_by(Message.timestamp)
        )
        messages = result.scalars().all()
        history = [{"role": m.role, "content": m.content} for m in messages]

        # Cargar en Redis para la sesión activa
        for msg in history:
            await append_to_history(session_id, msg["role"], msg["content"])

        logger.info(
            f"Historial cargado PostgreSQL→Redis — "
            f"session: {session_id} | mensajes: {len(history)}"
        )
        return history
    except Exception as e:
        logger.error(f"Error al cargar historial de sesión {session_id}: {e}")
        return []

async def create_session(
    user_id: int,
    model: str,
    db: AsyncSession
) -> Session:
    """
    Crea una nueva sesión vacía para el usuario autenticado.
    El título se genera automáticamente con el primer mensaje (Tarea 9).
    """
    session = Session(
        user_id=user_id,
        model_used=model,
        title="Nueva sesión",
        is_active=True,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    logger.info(f"Sesión creada — user_id: {user_id} | session: {session.id}")
    return session

async def list_sessions(user_id: int, db: AsyncSession) -> list[Session]:
    """
    Retorna todas las sesiones activas del usuario
    ordenadas por última actividad descendente.
    """
    result = await db.execute(
        select(Session)
        .where(Session.user_id == user_id, Session.is_active == True)
        .order_by(Session.last_active_at.desc())
    )
    return result.scalars().all()