"""Güvenlik yardımcıları — JWT, password hash, secret maskeleme."""

from __future__ import annotations

import hashlib
import re
import secrets
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

_MASK_PATTERN = re.compile(
    r"(password|token|key|secret|api_key)\s*[=:]\s*\S+",
    re.IGNORECASE,
)

pwd_context = CryptContext(schemes=["bcrypt", "sha512_crypt"], deprecated="auto")

ALGORITHM = "HS256"
API_KEY_HASH_PREFIX = "sha256:"


def verify_password(plain: str, hashed: str) -> bool:
    """Düz metin şifreyi hash ile karşılaştırır."""
    try:
        return pwd_context.verify(plain, hashed)
    except ValueError:
        return False


def hash_password(plain: str) -> str:
    """Düz metin şifreyi bcrypt ile hash'ler."""
    return pwd_context.hash(plain)


def hash_api_key(api_key: str) -> str:
    """Agent API anahtarını veritabanında saklanacak tek yönlü özetine çevirir."""
    normalized = api_key.strip()
    if not normalized:
        raise ValueError("api_key boş olamaz")
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"{API_KEY_HASH_PREFIX}{digest}"


def is_hashed_api_key(value: str) -> bool:
    """Değer yeni hash formatındaki bir agent API anahtarı mı?"""
    return value.startswith(API_KEY_HASH_PREFIX) and len(value) == len(API_KEY_HASH_PREFIX) + 64


def verify_api_key(plain: str, hashed: str) -> bool:
    """Agent API anahtarını hash ile sabit zamanda karşılaştırır."""
    if not is_hashed_api_key(hashed):
        return False
    return secrets.compare_digest(hash_api_key(plain), hashed)


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
