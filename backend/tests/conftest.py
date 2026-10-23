import os
import pytest
import pytest_asyncio
from pathlib import Path
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

# Temporary test sqlite database file
TEST_DB_FILE = Path(__file__).parent / "test_temp.db"
TEST_DB_URL = f"sqlite+aiosqlite:///{TEST_DB_FILE.as_posix()}"

os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["WORKSPACE_BASE_DIR"] = str(Path(__file__).parent / "test_workspace")
os.environ["ENABLE_LOCAL_DEV_RUNNER"] = "false"

# Re-import after setting env vars
import app.db.session as session_module
from app.db.base import Base
from app.main import app
from app.db.session import get_db

# Configure session_module engine to use test DB
session_module.engine = create_async_engine(
    TEST_DB_URL,
    echo=False,
    future=True,
    connect_args={"check_same_thread": False},
)
session_module.AsyncSessionLocal = async_sessionmaker(
    bind=session_module.engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_test_db():
    async with session_module.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with session_module.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    if TEST_DB_FILE.exists():
        try:
            TEST_DB_FILE.unlink()
        except Exception:
            pass


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with session_module.AsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c
