"""Server modeli."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.ai_analysis import AIAnalysis
    from app.models.alert import Alert
    from app.models.log_entry import LogEntry
    from app.models.metric import Metric
    from app.models.service_status import ServiceStatus


class Server(Base):
    """İzlenen sunucu kaydı."""

    __tablename__ = "servers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    hostname: Mapped[str] = mapped_column(String(255))
    ip_address: Mapped[str] = mapped_column(String(45))
    api_key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    environment: Mapped[str] = mapped_column(
        String(50), default="production", nullable=False, index=True
    )
    group_name: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    api_key_revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="offline")
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    metrics: Mapped[list[Metric]] = relationship(
        back_populates="server", cascade="all, delete-orphan"
    )
    alerts: Mapped[list[Alert]] = relationship(
        back_populates="server", cascade="all, delete-orphan"
    )
    services: Mapped[list[ServiceStatus]] = relationship(
        back_populates="server", cascade="all, delete-orphan"
    )
    log_entries: Mapped[list[LogEntry]] = relationship(
        back_populates="server", cascade="all, delete-orphan"
    )
    ai_analyses: Mapped[list[AIAnalysis]] = relationship(
        back_populates="server", cascade="all, delete-orphan"
    )
