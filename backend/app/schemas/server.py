"""Server, ServiceStatus ve LogEntry şemaları."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.metric import MetricOut

MAX_TAGS = 20
MAX_TAG_LENGTH = 40


def normalize_tags(tags: list[str]) -> list[str]:
    """Etiketleri kırpar, tekilleştirir ve boş değerleri atar."""
    normalized: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        value = tag.strip().lower()
        if not value or value in seen:
            continue
        if len(value) > MAX_TAG_LENGTH:
            raise ValueError(f"Tag max {MAX_TAG_LENGTH} karakter olabilir")
        seen.add(value)
        normalized.append(value)
    if len(normalized) > MAX_TAGS:
        raise ValueError(f"En fazla {MAX_TAGS} tag girilebilir")
    return normalized


class ServerCreate(BaseModel):
    """Yeni sunucu kayıt isteği."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    hostname: str = Field(min_length=1, max_length=255)
    ip_address: str = Field(min_length=7, max_length=45)
    environment: str = Field(default="production", min_length=1, max_length=50)
    group_name: str = Field(default="", max_length=100)
    tags: list[str] = Field(default_factory=list)

    @field_validator("environment")
    @classmethod
    def strip_environment(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("environment boş olamaz")
        return normalized

    @field_validator("group_name")
    @classmethod
    def strip_group_name(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: list[str]) -> list[str]:
        return normalize_tags(value)


class ServerCreatedOut(BaseModel):
    """Sunucu oluşturma yanıtı — api_key yalnızca bu yanıtta bir kez döner."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    hostname: str
    ip_address: str
    environment: str
    group_name: str
    tags: list[str]
    status: str
    api_key: str
    last_seen: datetime | None
    created_at: datetime


class ServerOut(BaseModel):
    """Sunucu listesi ve detay yanıtı — api_key asla döndürülmez."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    hostname: str
    ip_address: str
    environment: str
    group_name: str
    tags: list[str]
    status: str
    last_seen: datetime | None
    created_at: datetime
    latest_metric: MetricOut | None = None
    active_alert_count: int = 0
    critical_alert_count: int = 0


class ServerApiKeyOut(BaseModel):
    """Yeni/yenilenmiş agent API anahtarı yanıtı."""

    id: int
    api_key: str


class ServiceStatusOut(BaseModel):
    """Servis durum yanıtı."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    server_id: int
    service_name: str
    status: str
    checked_at: datetime


class LogEntryOut(BaseModel):
    """Log kaydı yanıtı — raw_line hariç (büyük olabilir)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    server_id: int
    source_file: str
    level: str
    message: str
    logged_at: datetime


class LogEntryDetailOut(LogEntryOut):
    """Tekil log detayı — raw satır dahil."""

    raw_line: str
