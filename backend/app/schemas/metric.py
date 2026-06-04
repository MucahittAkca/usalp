"""Metric şemaları — Agent payload'u ve API response'ları."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CpuData(BaseModel):
    """Agent'tan gelen CPU metrik yapısı."""

    model_config = ConfigDict(extra="forbid")

    percent: float = Field(ge=0, le=100)
    per_core: list[float] = Field(default_factory=list, max_length=256)
    load_avg_1: float = Field(default=0.0, ge=0)
    load_avg_5: float = Field(default=0.0, ge=0)
    load_avg_15: float = Field(default=0.0, ge=0)


class MemoryData(BaseModel):
    """Agent'tan gelen RAM metrik yapısı."""

    model_config = ConfigDict(extra="forbid")

    total_bytes: int = Field(ge=0)
    used_bytes: int = Field(ge=0)
    available_bytes: int = Field(ge=0)
    cached_bytes: int = Field(default=0, ge=0)
    percent: float = Field(ge=0, le=100)
    swap_total_bytes: int = Field(default=0, ge=0)
    swap_used_bytes: int = Field(default=0, ge=0)


class DiskData(BaseModel):
    """Agent'tan gelen tekil disk bölümü metriği."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1, max_length=512)
    total_bytes: int = Field(ge=0)
    used_bytes: int = Field(ge=0)
    free_bytes: int = Field(ge=0)
    percent: float = Field(ge=0, le=100)
    read_bytes_per_sec: float = Field(default=0.0, ge=0)
    write_bytes_per_sec: float = Field(default=0.0, ge=0)


class NetworkData(BaseModel):
    """Agent'tan gelen tekil ağ arayüzü metriği."""

    model_config = ConfigDict(extra="forbid")

    interface: str = Field(min_length=1, max_length=64)
    bytes_sent_per_sec: float = Field(ge=0)
    bytes_recv_per_sec: float = Field(ge=0)
    packets_sent_per_sec: float = Field(default=0.0, ge=0)
    packets_recv_per_sec: float = Field(default=0.0, ge=0)
    errors_in: int = Field(default=0, ge=0)
    errors_out: int = Field(default=0, ge=0)


class ProcessData(BaseModel):
    """Agent'tan gelen işlem bilgisi."""

    model_config = ConfigDict(extra="forbid")

    pid: int = Field(ge=0)
    name: str = Field(min_length=1, max_length=255)
    cpu_percent: float = Field(ge=0)
    memory_percent: float = Field(ge=0, le=100)
    status: str = Field(min_length=1, max_length=50)


class ServiceData(BaseModel):
    """Agent'tan gelen servis durum bilgisi."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    status: str = Field(min_length=1, max_length=50)
    sub_state: str = Field(default="", max_length=100)
    since_seconds: int | None = Field(default=None, ge=0)


class LogData(BaseModel):
    """Agent'tan gelen log satırı."""

    model_config = ConfigDict(extra="forbid")

    source_file: str = Field(min_length=1, max_length=512)
    level: str = Field(min_length=1, max_length=20)
    message: str = Field(default="", max_length=2_000)
    raw_line: str = Field(min_length=1, max_length=8_000)
    logged_at: datetime


class MetricPayload(BaseModel):
    """Agent'ın tek bir toplama döngüsünde gönderdiği birleşik payload."""

    model_config = ConfigDict(extra="forbid")

    server_id: str = Field(min_length=1, max_length=255)
    collected_at: datetime
    cpu: CpuData
    memory: MemoryData
    disks: list[DiskData] = Field(default_factory=list, max_length=128)
    networks: list[NetworkData] = Field(default_factory=list, max_length=128)
    top_processes: list[ProcessData] = Field(default_factory=list, max_length=50)
    services: list[ServiceData] = Field(default_factory=list, max_length=100)
    log_entries: list[LogData] = Field(default_factory=list, max_length=200)


class MetricOut(BaseModel):
    """Metrik API yanıtı — raw_json liste endpoint'lerinde döndürülmez."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    server_id: int
    cpu_percent: float
    ram_percent: float
    disk_percent: float
    network_in_bytes: int
    network_out_bytes: int
    load_avg_1: float
    load_avg_5: float
    load_avg_15: float
    recorded_at: datetime


class MetricDetailOut(MetricOut):
    """Tekil metrik detay yanıtı — tam payload dahil."""

    raw_json: dict[str, Any] | None = None
