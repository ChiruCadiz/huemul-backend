import sys
from loguru import logger

def setup_logger():
    logger.remove()

    # Terminal con colores
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

    # Archivo con rotación automática
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