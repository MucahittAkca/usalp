"""Kimlik doğrulama endpoint'i — Dashboard JWT token üretimi."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from fastapi import APIRouter, HTTPException, Request, status

from app.config import settings
from app.core.security import create_access_token, verify_password
from app.schemas.auth import TokenRequest, TokenResponse

router = APIRouter(tags=["auth"])
logger = logging.getLogger(__name__)


@dataclass
class _LoginAttempt:
    failures: int
    window_started_at: float
    locked_until: float = 0.0


_attempts: dict[str, _LoginAttempt] = {}


def _client_ip(request: Request) -> str:
    """İstekten güvenilir log/rate-limit IP değerini çıkarır."""
    forwarded_for = request.headers.get("x-forwarded-for", "")
    client_ip = forwarded_for.split(",", 1)[0].strip()
    if not client_ip and request.client:
        client_ip = request.client.host
    return client_ip or "unknown"


def _client_key(request: Request, username: str) -> str:
    """IP + kullanıcı adı bazlı rate-limit anahtarı üretir."""
    return f"{_client_ip(request)}:{username.lower()}"


def _check_rate_limit(key: str) -> None:
    """Çok sık başarısız login denemesini kısa süreli kilitler."""
    now = time.monotonic()
    attempt = _attempts.get(key)
    if not attempt:
        return

    if attempt.locked_until > now:
        retry_after = max(1, int(attempt.locked_until - now))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts",
            headers={"Retry-After": str(retry_after)},
        )

    if now - attempt.window_started_at > settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS:
        _attempts.pop(key, None)


def _record_login_failure(key: str) -> None:
    """Başarısız login'i pencere içinde sayar ve gerekirse kilitler."""
    now = time.monotonic()
    attempt = _attempts.get(key)
    if not attempt or now - attempt.window_started_at > settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS:
        attempt = _LoginAttempt(failures=0, window_started_at=now)
        _attempts[key] = attempt

    attempt.failures += 1
    if attempt.failures >= settings.LOGIN_RATE_LIMIT_ATTEMPTS:
        attempt.locked_until = now + settings.LOGIN_RATE_LIMIT_LOCK_SECONDS


def _record_login_success(key: str) -> None:
    """Başarılı login sonrası başarısız deneme sayacını temizler."""
    _attempts.pop(key, None)


def _has_outer_whitespace(value: str) -> bool:
    """Başta/sonda görünmez boşluk olup olmadığını güvenli loglamak için döner."""
    return value != value.strip()


@router.post("/auth/token", response_model=TokenResponse)
async def login(body: TokenRequest, request: Request) -> TokenResponse:
    """Kullanıcı adı/şifre ile JWT token üretir (tek kullanıcı, MVP)."""
    attempt_key = _client_key(request, body.username)
    _check_rate_limit(attempt_key)

    username_ok = body.username == settings.DASHBOARD_USERNAME
    password_ok = (
        verify_password(body.password, settings.DASHBOARD_PASSWORD_HASH)
        if settings.DASHBOARD_PASSWORD_HASH
        else body.password == settings.DASHBOARD_PASSWORD
    )
    if not username_ok or not password_ok:
        _record_login_failure(attempt_key)
        logger.warning(
            "Dashboard login failed: client_ip=%s username_match=%s password_match=%s "
            "supplied_username_length=%d configured_username_length=%d "
            "username_has_outer_whitespace=%s password_has_outer_whitespace=%s",
            _client_ip(request),
            username_ok,
            password_ok,
            len(body.username),
            len(settings.DASHBOARD_USERNAME),
            _has_outer_whitespace(body.username),
            _has_outer_whitespace(body.password),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    _record_login_success(attempt_key)
    token = create_access_token(subject=body.username)
    return TokenResponse(access_token=token)
