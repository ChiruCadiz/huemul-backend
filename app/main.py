from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger
from app.auth.router import router as auth_router
from app.admin.router import router as admin_router
from app.chat.router import router as chat_router
from app.models.router import router as models_router
from app.sessions.router import router as sessions_router
from app.db.init_db import init_db
from app.logger import setup_logger
from app.memory.redis_client import get_redis, close_redis
import time

setup_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando Huemul Backend...")
    await init_db()
    await get_redis()
    logger.info("Base de datos y Redis inicializados correctamente.")
    yield
    await close_redis()
    logger.info("Huemul Backend detenido.")

app = FastAPI(
    title="Huemul Backend",
    description="Asistente de código con IA para la universidad.",
    version="0.2.0",
    lifespan=lifespan
)

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
        logger.error(
            f"✗ {request.method} {request.url.path} "
            f"| Error: {e} | {duration}ms"
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Error interno del servidor."}
        )

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(chat_router)
app.include_router(models_router)
app.include_router(sessions_router)
@app.get("/health")
async def health():
    return {"status": "ok", "service": "huemul-backend"}