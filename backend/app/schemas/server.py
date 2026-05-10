"""Server, ServiceStatus ve LogEntry şemaları."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ServerCreate(BaseModel):
    """Yeni sunucu kayıt isteği."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    hostname: str = Field(min_length=1, max_length=255)
    ip_address: str = Field(min_length=7, max_length=45)


class ServerCreatedOut(BaseModel):
    """Sunucu oluşturma yanıtı — api_key yalnızca bu yanıtta bir kez döner."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    hostname: str
    ip_address: str
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
    status: str
    last_seen: datetime | None
    created_at: datetime


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
