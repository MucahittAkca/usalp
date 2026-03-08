"""Metric şemaları."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class MetricIn(BaseModel):
    """Agent'tan gelen metrik verisi."""

    cpu_percent: float
    ram_percent: float
    disk_percent: float
    network_in_bytes: int
    network_out_bytes: int
    load_avg_1: float = 0.0
    load_avg_5: float = 0.0
    load_avg_15: float = 0.0
    services: list[dict] | None = None
    logs: list[dict] | None = None


class MetricOut(BaseModel):
    """Metrik yanıtı."""

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

    model_config = {"from_attributes": True}
