import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import pytest
import pytest_asyncio
import redis.asyncio as redis_lib
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.db.database import Base, get_db
from app.db.models import User, Config
from app.auth.jwt import create_access_token
from app.memory.session import clear_session

# ── Base de datos en memoria para tests ───────────────────────
DATABASE_URL_TEST = "sqlite+aiosqlite:///:memory:"
engine_test = create_async_engine(DATABASE_URL_TEST, echo=False)
AsyncSessionTest = sessionmaker(
    engine_test, class_=AsyncSession, expire_on_commit=False
)

async def override_get_db():
    async with AsyncSessionTest() as session:
        try:
            yield session
        finally:
            await session.close()

app.dependency_overrides[get_db] = override_get_db

@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Crea tablas antes de cada test y las elimina al terminar."""
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionTest() as session:
        session.add(Config(key="system_prompt", value="Prompt de prueba."))
        session.add(Config(key="default_model", value="gemma4:26b"))  # ← actualizado
        await session.commit()

    yield

    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture(autouse=True)
async def setup_redis():
    """Limpia claves de test en Redis antes y después de cada test."""
    r = redis_lib.Redis(host="localhost", port=6379, decode_responses=True)
    keys = await r.keys("session:test-*")
    if keys:
        await r.delete(*keys)
    yield
    keys = await r.keys("session:test-*")
    if keys:
        await r.delete(*keys)
    await r.aclose()

@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as c:
        yield c

@pytest_asyncio.fixture
async def db_session():
    """Sesión de BD directa para testear funciones de service.py sin pasar por HTTP."""
    async with AsyncSessionTest() as session:
        yield session

@pytest_asyncio.fixture
async def session_cleanup():
    """Acumula UUIDs de sesiones creadas en tests para limpiar Redis al finalizar."""
    ids = []
    yield ids
    if ids:
        r = redis_lib.Redis(host="localhost", port=6379, decode_responses=True)
        for sid in ids:
            await r.delete(f"session:{sid}")
        await r.aclose()

@pytest_asyncio.fixture
async def admin_user():
    async with AsyncSessionTest() as session:
        user = User(
            username="admin",
            email="admin@uandresbello.edu",
            role="admin"
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

@pytest_asyncio.fixture
async def regular_user():
    async with AsyncSessionTest() as session:
        user = User(
            username="estudiante",
            email="estudiante@uandresbello.edu",
            role="user"
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

@pytest_asyncio.fixture
async def second_user():
    """Segundo usuario para tests de aislamiento entre sesiones."""
    async with AsyncSessionTest() as session:
        user = User(
            username="otro_estudiante",
            email="otro@unab.cl",
            role="user"
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

@pytest_asyncio.fixture
def admin_token(admin_user):
    return create_access_token({
        "sub": str(admin_user.id),
        "username": admin_user.username,
        "role": admin_user.role,
        "email": admin_user.email
    })

@pytest_asyncio.fixture
def user_token(regular_user):
    return create_access_token({
        "sub": str(regular_user.id),
        "username": regular_user.username,
        "role": regular_user.role,
        "email": regular_user.email
    })