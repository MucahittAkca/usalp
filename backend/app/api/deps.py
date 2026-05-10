"""Ortak API bağımlılıkları — Agent API key ve Dashboard JWT doğrulama."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import decode_access_token
from app.database import get_db
from app.models.server import Server

# --- Agent Auth: Authorization: Bearer <api_key> ---

_agent_key_header = APIKeyHeader(name="Authorization", auto_error=False)


async def verify_agent_api_key(
    authorization: str | None = Security(_agent_key_header),
    db: AsyncSession = Depends(get_db),
) -> Server:
    """Bearer <api_key> formatını doğrular, ilişkili Server nesnesini döndürür."""
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")

    token = authorization.removeprefix("Bearer").strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key format")

    server = await db.scalar(
        select(Server).where(
            Server.api_key == token,
            Server.api_key_revoked_at.is_(None),
        )
    )
    if not server:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    return server


# --- Dashboard Auth: OAuth2 Bearer JWT ---

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


async def get_current_user(
    token: str | None = Depends(_oauth2_scheme),
) -> str:
    """JWT token'dan kullanıcı adını çıkarır. Geçersizse 401 fırlatır."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = decode_access_token(token)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if username != settings.DASHBOARD_USERNAME:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return username
