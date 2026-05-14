"""Eski metrik, log, servis durumu ve AI analiz kayıtlarını temizler."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.time import utc_now_naive
from app.models.ai_analysis import AIAnalysis
from app.models.log_entry import LogEntry
from app.models.metric import Metric
from app.models.service_status import ServiceStatus


async def cleanup_old_records(db: AsyncSession) -> dict[str, int]:
    """Retention ayarlarına göre eski zaman serisi verilerini siler."""
    now = utc_now_naive()
    cleanup_plan = [
        (
            "metrics",
            delete(Metric).where(
                Metric.recorded_at < now - timedelta(days=settings.METRIC_RETENTION_DAYS)
            ),
        ),
        (
            "logs",
            delete(LogEntry).where(
                LogEntry.logged_at < now - timedelta(days=settings.LOG_RETENTION_DAYS)
            ),
        ),
        (
            "service_statuses",
            delete(ServiceStatus).where(
                ServiceStatus.checked_at
                < now - timedelta(days=settings.SERVICE_STATUS_RETENTION_DAYS)
            ),
        ),
        (
            "ai_analyses",
            delete(AIAnalysis).where(
                AIAnalysis.created_at < now - timedelta(days=settings.AI_ANALYSIS_RETENTION_DAYS)
            ),
        ),
    ]

    deleted: dict[str, int] = {}
    for key, stmt in cleanup_plan:
        result = await db.execute(stmt)
        deleted[key] = result.rowcount or 0
    return deleted
