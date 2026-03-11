"""Metric modeli."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, Float, ForeignKey, Index, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.server import Server


class Metric(Base):
    """Sunucu performans metriği."""

    __tablename__ = "metrics"
    __table_args__ = (
        Index("ix_metrics_server_recorded", "server_id", "recorded_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    server_id: Mapped[int] = mapped_column(
        ForeignKey("servers.id", ondelete="CASCADE")
    )
    cpu_percent: Mapped[float] = mapped_column(Float)
    ram_percent: Mapped[float] = mapped_column(Float)
    disk_percent: Mapped[float] = mapped_column(Float)
    network_in_bytes: Mapped[int] = mapped_column(BigInteger)
    network_out_bytes: Mapped[int] = mapped_column(BigInteger)
    load_avg_1: Mapped[float] = mapped_column(Float)
    load_avg_5: Mapped[float] = mapped_column(Float)
    load_avg_15: Mapped[float] = mapped_column(Float)
    raw_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)

    server: Mapped[Server] = relationship(back_populates="metrics")
