from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.auth.router import router as auth_router
from app.admin.router import router as admin_router
from app.db.init_db import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(
    title="Huemul Backend",
    description="Asistente de código con IA para la universidad.",
    version="0.1.0",
    lifespan=lifespan
)

app.include_router(auth_router)
app.include_router(admin_router)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "huemul-backend"}