import redis.asyncio as redis
from loguru import logger
from app.config import settings

_redis_client = None

async def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                password=settings.redis_password or None,
                decode_responses=True,
            )
            await _redis_client.ping()
            logger.info("Conexión a Redis establecida correctamente.")
        except Exception as e:
            logger.error(f"Error al conectar con Redis: {e}")
            raise
    return _redis_client

async def close_redis():
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None
        logger.info("Conexión a Redis cerrada.")