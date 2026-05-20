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