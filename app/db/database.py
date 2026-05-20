from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=True,
    connect_args={
        "ssl": "require",
        "statement_cache_size": 0,  # ← soluciona incompatibilidad con PgBouncer de Supabase
    }
)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()