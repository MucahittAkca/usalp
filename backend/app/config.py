"""Uygulama konfigürasyonu — environment variable'lardan okunur."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Usalp Backend konfigürasyonu."""

    DATABASE_URL: str = "postgresql+asyncpg://usalp:usalp@localhost:5432/usalp"
    LLM_API_KEY: str = ""
    SECRET_KEY: str = "change-me-in-production"
    ENVIRONMENT: str = "development"

    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost"]

    # Dashboard tek kullanıcı auth (MVP)
    DASHBOARD_USERNAME: str = "admin"
    DASHBOARD_PASSWORD: str = "admin"
    JWT_EXPIRE_HOURS: int = 24

    # Alarm eşikleri
    ALERT_CPU_WARNING: float = 80.0
    ALERT_CPU_CRITICAL: float = 90.0
    ALERT_RAM_WARNING: float = 85.0
    ALERT_RAM_CRITICAL: float = 95.0
    ALERT_DISK_WARNING: float = 85.0
    ALERT_DISK_CRITICAL: float = 95.0

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
