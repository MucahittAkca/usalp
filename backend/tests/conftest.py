"""Test konfigürasyonu — izole async DB session, HTTP istemcisi ve JWT token."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import create_access_token
from app.database import Base, get_db
from app.main import app
from app.models import *  # noqa: F401,F403


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Her test için izole in-memory SQLite veritabanı oluşturur."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Test HTTP istemcisi — gerçek DB yerine in-memory session kullanır."""

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def jwt_token() -> str:
    """Geçerli bir Dashboard JWT token üretir."""
    return create_access_token(subject="admin")


@pytest.fixture
def auth_headers(jwt_token: str) -> dict[str, str]:
    """Dashboard endpoint'leri için Authorization header döndürür."""
    return {"Authorization": f"Bearer {jwt_token}"}
