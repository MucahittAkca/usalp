"""Server, ServiceStatus ve LogEntry şemaları."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ServerOut(BaseModel):
    """Sunucu listesi ve detay yanıtı — api_key asla döndürülmez."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    hostname: str
    ip_address: str
    status: str
    created_at: datetime


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
