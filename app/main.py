from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger
from app.auth.router import router as auth_router
from app.admin.router import router as admin_router
from app.chat.router import router as chat_router
from app.models.router import router as models_router
from app.db.init_db import init_db
from app.logger import setup_logger, setup_sentry
from app.memory.redis_client import get_redis, close_redis
import time
import sentry_sdk

# Inicializar logger y Sentry al importar el módulo
setup_logger()
setup_sentry()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando Huemul Backend...")
    await init_db()
    await get_redis()  # Inicializar Redis al inicio
    logger.info("Base de datos y Redis inicializados correctamente.")
    yield
    await close_redis()  # Cerrar conexión a Redis al finalizar
    logger.info("Huemul Backend detenido.")

app = FastAPI(
    title="Huemul Backend",
    description="Asistente de código con IA para la universidad.",
    version="0.1.0",
    lifespan=lifespan
)

# ── Middleware: log de todas las requests entrantes ────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    logger.info(f"→ {request.method} {request.url.path}")
    try:
        response = await call_next(request)
        duration = round((time.time() - start) * 1000, 2)
        logger.info(
            f"← {request.method} {request.url.path} "
            f"| status={response.status_code} | {duration}ms"
        )
        return response
    except Exception as e:
        duration = round((time.time() - start) * 1000, 2)
        logger.error(f"✗ {request.method} {request.url.path} | Error: {e} | {duration}ms")
        sentry_sdk.capture_exception(e)
        return JSONResponse(status_code=500, content={"detail": "Error interno del servidor."})

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(chat_router)
app.include_router(models_router)

@app.get("/health")
async def health():
    logger.debug("Health check solicitado.")
    return {"status": "ok", "service": "huemul-backend"}