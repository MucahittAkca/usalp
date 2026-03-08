"""Metric modeli."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Float, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Metric(Base):
    """Sunucu performans metriği."""

    __tablename__ = "metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    server_id: Mapped[int] = mapped_column(ForeignKey("servers.id"))
    cpu_percent: Mapped[float] = mapped_column(Float)
    ram_percent: Mapped[float] = mapped_column(Float)
    disk_percent: Mapped[float] = mapped_column(Float)
    network_in_bytes: Mapped[int] = mapped_column(BigInteger)
    network_out_bytes: Mapped[int] = mapped_column(BigInteger)
    load_avg_1: Mapped[float] = mapped_column(Float)
    load_avg_5: Mapped[float] = mapped_column(Float)
    load_avg_15: Mapped[float] = mapped_column(Float)
    recorded_at: Mapped[datetime] = mapped_column(server_default=func.now())
