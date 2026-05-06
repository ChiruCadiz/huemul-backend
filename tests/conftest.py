import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.db.database import Base, get_db
from app.db.models import User, Config

# Base de datos en memoria para tests
DATABASE_URL_TEST = "sqlite+aiosqlite:///:memory:"

engine_test = create_async_engine(DATABASE_URL_TEST, echo=False)
AsyncSessionTest = sessionmaker(engine_test, class_=AsyncSession, expire_on_commit=False)

async def override_get_db():
    async with AsyncSessionTest() as session:
        try:
            yield session
        finally:
            await session.close()

app.dependency_overrides[get_db] = override_get_db

@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Crea las tablas antes de cada test y las elimina al terminar."""
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Insertar datos iniciales
    async with AsyncSessionTest() as session:
        session.add(Config(key="system_prompt", value="Prompt de prueba."))
        await session.commit()

    yield

    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as c:
        yield c

@pytest_asyncio.fixture
async def admin_user():
    """Crea un usuario admin para tests que lo requieren."""
    async with AsyncSessionTest() as session:
        user = User(username="admin", email="admin@uandresbello.edu", role="admin")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

@pytest_asyncio.fixture
async def regular_user():
    """Crea un usuario estándar para tests."""
    async with AsyncSessionTest() as session:
        user = User(username="estudiante", email="estudiante@uandresbello.edu", role="user")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user