"""Güvenlik yardımcıları — JWT, password hash, secret maskeleme."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

_MASK_PATTERN = re.compile(
    r"(password|token|key|secret|api_key)\s*[=:]\s*\S+",
    re.IGNORECASE,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


def verify_password(plain: str, hashed: str) -> bool:
    """Düz metin şifreyi hash ile karşılaştırır."""
    return pwd_context.verify(plain, hashed)


def hash_password(plain: str) -> str:
    """Düz metin şifreyi bcrypt ile hash'ler."""
    return pwd_context.hash(plain)


def create_access_token(subject: str, *, expires_delta: timedelta | None = None) -> str:
    """JWT access token oluşturur."""
    expire = datetime.now(UTC) + (expires_delta or timedelta(hours=settings.JWT_EXPIRE_HOURS))
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> str | None:
    """JWT token'ı çözer, geçerliyse subject döner, değilse None."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


def mask_secrets(text: str) -> str:
    """Log satırlarında hassas bilgileri maskeler."""
    return _MASK_PATTERN.sub(r"\1=***MASKED***", text)
