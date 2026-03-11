"""ServiceStatus modeli."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.server import Server


class ServiceStatus(Base):
    """Systemd servis durum kaydı."""

    __tablename__ = "service_statuses"

    id: Mapped[int] = mapped_column(primary_key=True)
    server_id: Mapped[int] = mapped_column(
        ForeignKey("servers.id", ondelete="CASCADE")
    )
    service_name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50))
    checked_at: Mapped[datetime] = mapped_column(server_default=func.now())

    server: Mapped[Server] = relationship(back_populates="services")
