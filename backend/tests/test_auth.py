"""Auth endpoint testleri — JWT token üretimi ve doğrulama."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from httpx import AsyncClient

from app.api.auth import _attempts
from app.config import settings


@pytest.fixture(autouse=True)
def clear_login_attempts() -> Iterator[None]:
    """Login rate-limit state testler arasında sızmasın."""
    _attempts.clear()
    yield
    _attempts.clear()


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient) -> None:
    """Doğru kimlik bilgileri ile JWT token döner."""
    resp = await client.post(
        "/api/v1/auth/token",
        json={"username": "admin", "password": "admin"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient) -> None:
    """Yanlış şifre ile 401 döner."""
    resp = await client.post(
        "/api/v1/auth/token",
        json={"username": "admin", "password": "wrong"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_wrong_username(client: AsyncClient) -> None:
    """Yanlış kullanıcı adı ile 401 döner."""
    resp = await client.post(
        "/api/v1/auth/token",
        json={"username": "hacker", "password": "admin"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_missing_fields(client: AsyncClient) -> None:
    """Eksik alanlar ile 422 döner."""
    resp = await client.post("/api/v1/auth/token", json={"username": "admin"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_rate_limit_after_repeated_failures(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ardışık başarısız login denemeleri 429 ile kısa süreli kilitlenir."""
    monkeypatch.setattr(settings, "LOGIN_RATE_LIMIT_ATTEMPTS", 2)
    monkeypatch.setattr(settings, "LOGIN_RATE_LIMIT_WINDOW_SECONDS", 60)
    monkeypatch.setattr(settings, "LOGIN_RATE_LIMIT_LOCK_SECONDS", 30)

    for _ in range(2):
        resp = await client.post(
            "/api/v1/auth/token",
            json={"username": "admin", "password": "wrong"},
        )
        assert resp.status_code == 401

    locked = await client.post(
        "/api/v1/auth/token",
        json={"username": "admin", "password": "admin"},
    )
    assert locked.status_code == 429
    assert "Retry-After" in locked.headers


@pytest.mark.asyncio
async def test_protected_endpoint_no_token(client: AsyncClient) -> None:
    """Token olmadan dashboard endpoint'ine erişim 401 döner."""
    resp = await client.get("/api/v1/servers")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_invalid_token(client: AsyncClient) -> None:
    """Geçersiz token ile 401 döner."""
    resp = await client.get(
        "/api/v1/servers",
        headers={"Authorization": "Bearer invalid.token.here"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_valid_token(client: AsyncClient, auth_headers: dict) -> None:
    """Geçerli token ile dashboard endpoint'i 200 döner."""
    resp = await client.get("/api/v1/servers", headers=auth_headers)
    assert resp.status_code == 200
