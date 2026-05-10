"""Sunucu heartbeat ve offline durum bakım işlemleri."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.server import Server


async def mark_stale_servers_offline(db: AsyncSession) -> int:
    """Belirlenen süre boyunca heartbeat almayan sunucuları offline yapar."""
    cutoff = datetime.now(UTC) - timedelta(seconds=settings.SERVER_OFFLINE_AFTER_SECONDS)
    stmt = (
        update(Server)
        .where(
            Server.status != "offline",
            Server.last_seen.isnot(None),
            Server.last_seen < cutoff,
        )
        .values(status="offline")
    )
    result = await db.execute(stmt)
    return result.rowcount or 0
