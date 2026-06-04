"""Uygulama konfigürasyonu — environment variable'lardan okunur."""

from __future__ import annotations

import json
import re
from urllib.parse import urlparse

from pydantic_settings import BaseSettings

_BCRYPT_RE = re.compile(r"^\$2[abxy]\$\d{2}\$[./A-Za-z0-9]{53}$")
_SHA512_CRYPT_RE = re.compile(r"^\$6\$[./A-Za-z0-9]{1,16}\$[./A-Za-z0-9]{86}$")


def _split_origins(value: str) -> list[str]:
    """JSON array veya comma-separated CORS değerlerini güvenli parse eder."""
    stripped = value.strip()
    if stripped.startswith("["):
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError("CORS_ORIGINS JSON array veya comma-separated origin olmalıdır.") from exc
        if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
            raise ValueError("CORS_ORIGINS JSON array yalnızca string origin içermelidir.")
        return [origin.strip() for origin in parsed if origin.strip()]
    return [origin.strip() for origin in value.split(",") if origin.strip()]

class Settings(BaseSettings):
    """Usalp Backend konfigürasyonu."""

    DATABASE_URL: str = "postgresql+asyncpg://usalp:usalp@localhost:5432/usalp"
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://openrouter.ai/api"
    LLM_MODEL: str = "anthropic/claude-sonnet-4"
    SECRET_KEY: str = "change-me-in-production"
    ENVIRONMENT: str = "development"
    USALP_PUBLIC_URL: str = "http://localhost"
    MAX_REQUEST_BODY_BYTES: int = 1_048_576

    CORS_ORIGINS: str = "http://localhost:3000,http://localhost"

    # Dashboard tek kullanıcı auth (MVP)
    DASHBOARD_USERNAME: str = "admin"
    DASHBOARD_PASSWORD: str = "admin"
    DASHBOARD_PASSWORD_HASH: str = ""
    JWT_EXPIRE_HOURS: int = 24
    LOGIN_RATE_LIMIT_ATTEMPTS: int = 5
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = 60
    LOGIN_RATE_LIMIT_LOCK_SECONDS: int = 300

    # Sunucu durum takibi
    SERVER_OFFLINE_AFTER_SECONDS: int = 120

    # Alarm eşikleri
    ALERT_CPU_WARNING: float = 80.0
    ALERT_CPU_CRITICAL: float = 90.0
    ALERT_RAM_WARNING: float = 85.0
    ALERT_RAM_CRITICAL: float = 95.0
    ALERT_DISK_WARNING: float = 85.0
    ALERT_DISK_CRITICAL: float = 95.0

    # Alert bildirimleri (kanal alanları boşsa ilgili kanal devre dışı kalır)
    ALERT_NOTIFICATIONS_ENABLED: bool = True
    ALERT_NOTIFICATION_TIMEOUT_SECONDS: float = 5.0
    ALERT_EMAIL_HOST: str = ""
    ALERT_EMAIL_PORT: int = 587
    ALERT_EMAIL_USERNAME: str = ""
    ALERT_EMAIL_PASSWORD: str = ""
    ALERT_EMAIL_FROM: str = ""
    ALERT_EMAIL_TO: str = ""
    ALERT_EMAIL_USE_SSL: bool = False
    ALERT_EMAIL_STARTTLS: bool = True
    ALERT_TELEGRAM_BOT_TOKEN: str = ""
    ALERT_TELEGRAM_CHAT_ID: str = ""
    ALERT_SLACK_WEBHOOK_URL: str = ""

    # Veri saklama / bakım
    METRIC_RETENTION_DAYS: int = 30
    LOG_RETENTION_DAYS: int = 14
    SERVICE_STATUS_RETENTION_DAYS: int = 7
    AI_ANALYSIS_RETENTION_DAYS: int = 90
    RETENTION_SWEEP_INTERVAL_SECONDS: int = 3600

    # Demo modu
    DEMO_MODE: bool = False
    DEMO_SEED_RESET: bool = True

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def cors_origins(self) -> list[str]:
        """CORS_ORIGINS'i comma-separated veya tek URL olarak listeye çevirir."""
        return _split_origins(self.CORS_ORIGINS)

    def model_post_init(self, __context: object) -> None:
        """Production ortamında güvenli varsayılanları zorunlu kılar."""
        env = self.ENVIRONMENT.lower()
        parsed_public_url = urlparse(self.USALP_PUBLIC_URL)
        if env == "production" and (
            parsed_public_url.scheme != "https" or not parsed_public_url.netloc
        ):
            raise ValueError("Production ortamında USALP_PUBLIC_URL geçerli bir https URL olmalıdır.")

        origins = self.cors_origins
        if not origins:
            raise ValueError("CORS_ORIGINS en az bir origin içermelidir.")
        for origin in origins:
            parsed = urlparse(origin)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError(f"Geçersiz CORS_ORIGINS değeri: {origin}")

        if self.DASHBOARD_PASSWORD_HASH and not (
            _BCRYPT_RE.match(self.DASHBOARD_PASSWORD_HASH)
            or _SHA512_CRYPT_RE.match(self.DASHBOARD_PASSWORD_HASH)
        ):
            raise ValueError("DASHBOARD_PASSWORD_HASH bcrypt veya sha512-crypt formatında olmalıdır.")

        if env != "production":
            return

        secret = self.SECRET_KEY.strip()
        insecure_secret = (
            len(secret) < 32
            or secret in {"change-me-in-production", "change_me_32_byte_hex"}
            or "change" in secret.lower()
            or len(set(secret)) < 12
        )
        insecure_password = not self.DASHBOARD_PASSWORD_HASH
        if insecure_secret or insecure_password or self.DEMO_MODE:
            raise ValueError(
                "Production ortamında SECRET_KEY ve DASHBOARD_PASSWORD_HASH "
                "güvenli değerlerle tanımlanmalı ve DEMO_MODE kapalı olmalıdır."
            )


settings = Settings()
