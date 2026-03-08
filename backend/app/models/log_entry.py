"""LogEntry modeli."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LogEntry(Base):
    """Sunucudan toplanan log satırı."""

    __tablename__ = "log_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    server_id: Mapped[int] = mapped_column(ForeignKey("servers.id"))
    source_file: Mapped[str] = mapped_column(String(512))
    level: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(Text, default="")
    raw_line: Mapped[str] = mapped_column(Text)
    logged_at: Mapped[datetime] = mapped_column(server_default=func.now())
