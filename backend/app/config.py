"""Uygulama konfigürasyonu — environment variable'lardan okunur."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Usalp Backend konfigürasyonu."""

    DATABASE_URL: str = "postgresql+asyncpg://usalp:usalp@localhost:5432/usalp"
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://openrouter.ai/api"
    LLM_MODEL: str = "anthropic/claude-sonnet-4-20250514"
    SECRET_KEY: str = "change-me-in-production"
    ENVIRONMENT: str = "development"

    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost"]

    # Dashboard tek kullanıcı auth (MVP)
    DASHBOARD_USERNAME: str = "admin"
    DASHBOARD_PASSWORD: str = "admin"
    DASHBOARD_PASSWORD_HASH: str = ""
    JWT_EXPIRE_HOURS: int = 24

    # Sunucu durum takibi
    SERVER_OFFLINE_AFTER_SECONDS: int = 120

    # Alarm eşikleri
    ALERT_CPU_WARNING: float = 80.0
    ALERT_CPU_CRITICAL: float = 90.0
    ALERT_RAM_WARNING: float = 85.0
    ALERT_RAM_CRITICAL: float = 95.0
    ALERT_DISK_WARNING: float = 85.0
    ALERT_DISK_CRITICAL: float = 95.0

    # Veri saklama / bakım
    METRIC_RETENTION_DAYS: int = 30
    LOG_RETENTION_DAYS: int = 14
    SERVICE_STATUS_RETENTION_DAYS: int = 7
    AI_ANALYSIS_RETENTION_DAYS: int = 90
    RETENTION_SWEEP_INTERVAL_SECONDS: int = 3600

    model_config = {"env_file": ".env", "extra": "ignore"}

    def model_post_init(self, __context: object) -> None:
        """Production ortamında güvenli varsayılanları zorunlu kılar."""
        if self.ENVIRONMENT.lower() != "production":
            return

        insecure_secret = self.SECRET_KEY in {"change-me-in-production", "change_me_32_byte_hex"}
        insecure_password = (
            not self.DASHBOARD_PASSWORD_HASH
            and self.DASHBOARD_USERNAME == "admin"
            and self.DASHBOARD_PASSWORD == "admin"
        )
        if insecure_secret or insecure_password:
            raise ValueError(
                "Production ortamında SECRET_KEY ve dashboard şifresi/hash'i "
                "güvenli değerlerle tanımlanmalıdır."
            )


settings = Settings()
