from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import event
from app.config import settings
from app.db.base import Base

# Create async engine with proper SQLite foreign keys enforcement
engine = create_async_engine(
    settings.normalized_database_url,
    echo=settings.DEBUG,
    future=True,
)

# Enforce foreign key constraints on SQLite connections
if "sqlite" in settings.DATABASE_URL:
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_database():
    """Initializes database schema and ensures tables exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
