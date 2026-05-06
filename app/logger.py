import sys
from loguru import logger
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from app.config import settings

def setup_sentry():
    if not settings.sentry_dsn:
        logger.warning("SENTRY_DSN no configurado — Sentry desactivado.")
        return

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        integrations=[
            FastApiIntegration(),       # Captura errores de FastAPI automáticamente
            SqlalchemyIntegration(),    # Captura errores de SQLAlchemy
        ],
        traces_sample_rate=1.0,        # 100% de trazas en desarrollo
        send_default_pii=False,        # No enviar info personal a Sentry
    )
    logger.info("Sentry inicializado correctamente.")

def setup_logger():
    logger.remove()

    # Terminal
    logger.add(
        sys.stdout,
        level="DEBUG",
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        colorize=True,
    )

    # Archivo con rotación
    logger.add(
        "logs/huemul.log",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} | {message}",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
    )

    return logger