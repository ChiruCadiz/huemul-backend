import json
from loguru import logger
from app.memory.redis_client import get_redis
from app.config import settings

SESSION_PREFIX = "session:"

async def get_session_history(session_id: str) -> list[dict]:
    """
    Recupera el historial de mensajes de una sesión desde Redis.
    Retorna lista de dicts: [{ role: "user"|"assistant", content: "..." }]
    Si no existe la sesión retorna lista vacía.
    """
    redis = await get_redis()
    key = f"{SESSION_PREFIX}{session_id}"
    try:
        data = await redis.get(key)
        if not data:
            logger.debug(f"Sesión {session_id} no encontrada en Redis — historial vacío.")
            return []
        history = json.loads(data)
        logger.debug(f"Historial recuperado — session: {session_id} | mensajes: {len(history)}")
        return history
    except Exception as e:
        logger.error(f"Error al recuperar historial de sesión {session_id}: {e}")
        return []

async def append_to_history(session_id: str, role: str, content: str) -> None:
    """
    Agrega un mensaje al historial de la sesión en Redis.
    role: "user" o "assistant"
    Renueva el TTL en cada escritura.
    """
    redis = await get_redis()
    key = f"{SESSION_PREFIX}{session_id}"
    try:
        history = await get_session_history(session_id)
        history.append({"role": role, "content": content})
        ttl_seconds = settings.redis_ttl_hours * 3600
        await redis.setex(key, ttl_seconds, json.dumps(history))
        logger.debug(
            f"Mensaje guardado — session: {session_id} | "
            f"role: {role} | total mensajes: {len(history)}"
        )
    except Exception as e:
        logger.error(f"Error al guardar mensaje en sesión {session_id}: {e}")

async def clear_session(session_id: str) -> None:
    """Elimina el historial de una sesión de Redis."""
    redis = await get_redis()
    key = f"{SESSION_PREFIX}{session_id}"
    await redis.delete(key)
    logger.info(f"Sesión {session_id} eliminada de Redis.")