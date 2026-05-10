"""Kimlik doğrulama endpoint'i — Dashboard JWT token üretimi."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.config import settings
from app.core.security import create_access_token, verify_password
from app.schemas.auth import TokenRequest, TokenResponse

router = APIRouter(tags=["auth"])


@router.post("/auth/token", response_model=TokenResponse)
async def login(body: TokenRequest) -> TokenResponse:
    """Kullanıcı adı/şifre ile JWT token üretir (tek kullanıcı, MVP)."""
    password_ok = (
        verify_password(body.password, settings.DASHBOARD_PASSWORD_HASH)
        if settings.DASHBOARD_PASSWORD_HASH
        else body.password == settings.DASHBOARD_PASSWORD
    )
    if body.username != settings.DASHBOARD_USERNAME or not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    token = create_access_token(subject=body.username)
    return TokenResponse(access_token=token)
