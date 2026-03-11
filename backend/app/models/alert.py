"""Alert modeli."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.ai_analysis import AIAnalysis
    from app.models.server import Server


class Alert(Base):
    """Eşik aşımı veya servis hatası alarmı."""

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    server_id: Mapped[int] = mapped_column(
        ForeignKey("servers.id", ondelete="CASCADE")
    )
    type: Mapped[str] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(Text)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    server: Mapped[Server] = relationship(back_populates="alerts")
    ai_analysis: Mapped[AIAnalysis | None] = relationship(
        back_populates="alert", uselist=False
    )
