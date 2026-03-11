"""Agent payload modelleri.

Backend API'ye gönderilen tüm metrik, servis, log ve
üst-düzey payload yapılarını tanımlar.
"""

from datetime import UTC, datetime
from typing import Optional

from pydantic import BaseModel, Field


class CpuMetrics(BaseModel):
    """Toplam ve çekirdek bazında CPU kullanım metrikleri."""

    percent: float
    per_core: list[float]
    load_avg_1: float
    load_avg_5: float
    load_avg_15: float


class MemoryMetrics(BaseModel):
    """RAM ve swap bellek kullanım metrikleri (byte cinsinden)."""

    total_bytes: int
    used_bytes: int
    available_bytes: int
    cached_bytes: int
    percent: float
    swap_total_bytes: int
    swap_used_bytes: int


class DiskMetrics(BaseModel):
    """Tek bir mount-point için disk kullanımı ve I/O hızı."""

    path: str
    total_bytes: int
    used_bytes: int
    free_bytes: int
    percent: float
    read_bytes_per_sec: float
    write_bytes_per_sec: float


class NetworkMetrics(BaseModel):
    """Tek bir ağ arayüzü için trafik ve hata istatistikleri."""

    interface: str
    bytes_sent_per_sec: float
    bytes_recv_per_sec: float
    packets_sent_per_sec: float
    packets_recv_per_sec: float
    errors_in: int
    errors_out: int


class ProcessInfo(BaseModel):
    """Kaynak tüketimi yüksek tek bir işlemin özet bilgisi."""

    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    status: str


class ServiceStatus(BaseModel):
    """systemd servisinin anlık durum bilgisi."""

    name: str
    status: str
    sub_state: str
    since_seconds: Optional[int] = None


class LogEntry(BaseModel):
    """Hata seviyesine uyan tek bir log satırı."""

    source_file: str
    level: str
    message: str
    raw_line: str
    logged_at: datetime


class MetricPayload(BaseModel):
    """Agent'ın tek bir toplama döngüsünde ürettiği birleşik payload."""

    server_id: str
    collected_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    cpu: CpuMetrics
    memory: MemoryMetrics
    disks: list[DiskMetrics]
    networks: list[NetworkMetrics]
    top_processes: list[ProcessInfo]
    services: list[ServiceStatus]
    log_entries: list[LogEntry]
