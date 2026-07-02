from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env")

    database_url: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 8
    environment: str = "development"
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    redis_ttl_hours: int = 24
    ollama_base_url: str = "http://200.27.101.243:11434"

    # ── Nuevo: SMTP para recuperación de contraseña ────────
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""

settings = Settings()

async def get_max_context(db) -> int:
    from app.db.models import Config
    from sqlalchemy import select
    result = await db.execute(
        select(Config).where(Config.key == "max_context_chars")
    )
    config = result.scalar_one_or_none()
    try:
        return int(config.value) if config else 12000
    except (ValueError, AttributeError):
        return 12000