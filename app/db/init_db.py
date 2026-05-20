from app.db.database import engine, Base, AsyncSessionLocal
from app.db import models
from sqlalchemy import select
from loguru import logger

async def init_db():
    # ── Paso 1: Crear tablas ───────────────────────────────────
    # create_all() revisa qué tablas existen en la BD y crea
    # las que faltan. Si ya existen, no las toca.
    # Esto permite que el backend sea autosuficiente al arrancar
    # sin necesidad de correr migraciones manualmente.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # ── Paso 2: Datos iniciales ────────────────────────────────
    # Verificamos e insertamos registros por defecto en la tabla
    # config solo si no existen. Esto evita duplicados si el
    # backend se reinicia múltiples veces.
    async with AsyncSessionLocal() as session:

        # ── system_prompt ──────────────────────────────────────
        # El system_prompt es el texto que se incluye al inicio
        # de cada conversación con Ollama para definir el
        # comportamiento institucional del agente.
        r1 = await session.execute(
            select(models.Config).where(models.Config.key == "system_prompt")
        )
        existing = r1.scalar_one_or_none()

        if not existing:
            # No existe → lo insertamos con el valor por defecto
            session.add(models.Config(
                key="system_prompt",
                value="Eres Huemul, un asistente de código de la universidad. "
                      "Responde siempre en español y con enfoque académico."
            ))
            await session.commit()
            logger.info("system_prompt insertado con valor por defecto.")
        else:
            # Ya existe → solo logueamos los primeros 50 caracteres
            # para confirmar que se está leyendo correctamente
            logger.info(f"system_prompt encontrado: {existing.value[:50]}...")

        # ── default_model ──────────────────────────────────────
        # El default_model es el modelo de Ollama que se usa
        # cuando el usuario no selecciona uno explícitamente.
        # El administrador puede cambiarlo via PUT /admin/config.
        r2 = await session.execute(
            select(models.Config).where(models.Config.key == "default_model")
        )
        existing2 = r2.scalar_one_or_none()

        if not existing2:
            # No existe → lo insertamos con codellama como defecto
            session.add(models.Config(key="default_model", value="codellama"))
            await session.commit()
            logger.info("default_model insertado con valor por defecto.")
        else:
            # Ya existe → logueamos el valor actual para confirmación
            logger.info(f"default_model encontrado: {existing2.value}")