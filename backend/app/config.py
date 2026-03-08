"""Uygulama konfigürasyonu — environment variable'lardan okunur."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Usalp Backend konfigürasyonu."""

    DATABASE_URL: str = "postgresql+asyncpg://usalp:usalp@localhost:5432/usalp"
    LLM_API_KEY: str = ""
    AGENT_API_KEY: str = "usalp-agent-default"
    SECRET_KEY: str = "change-me-in-production"
    ENVIRONMENT: str = "development"

    # Alarm eşikleri
    ALERT_CPU_WARNING: int = 80
    ALERT_CPU_CRITICAL: int = 90
    ALERT_RAM_WARNING: int = 85
    ALERT_RAM_CRITICAL: int = 95
    ALERT_DISK_WARNING: int = 85
    ALERT_DISK_CRITICAL: int = 95

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
