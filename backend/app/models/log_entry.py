"""LogEntry modeli."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.server import Server


class LogEntry(Base):
    """Sunucudan toplanan log satırı."""

    __tablename__ = "log_entries"
    __table_args__ = (
        Index("ix_logs_server_logged", "server_id", "logged_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    server_id: Mapped[int] = mapped_column(
        ForeignKey("servers.id", ondelete="CASCADE")
    )
    source_file: Mapped[str] = mapped_column(String(512))
    level: Mapped[str] = mapped_column(String(20), index=True)
    message: Mapped[str] = mapped_column(Text, default="")
    raw_line: Mapped[str] = mapped_column(Text)
    logged_at: Mapped[datetime] = mapped_column(server_default=func.now())

    server: Mapped[Server] = relationship(back_populates="log_entries")
