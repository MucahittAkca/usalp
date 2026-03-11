"""Auth endpoint testleri — JWT token üretimi ve doğrulama."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


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
