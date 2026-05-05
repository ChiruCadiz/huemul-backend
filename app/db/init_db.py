from app.db.database import engine, Base, AsyncSessionLocal
from app.db import models
from sqlalchemy import select

async def init_db():
    # Crea las tablas users y config si no existen
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Inserta system_prompt por defecto solo si no existe
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(models.Config).where(models.Config.key == "system_prompt")
        )
        if not result.scalar_one_or_none():
            session.add(models.Config(
                key="system_prompt",
                value="Eres Huemul, un asistente de código de la universidad. "
                      "Responde siempre en español y con enfoque académico."
            ))
            await session.commit()