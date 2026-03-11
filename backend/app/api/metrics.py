"""Metrik endpoint'leri — Agent'tan veri alımı."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import verify_agent_api_key
from app.database import get_db
from app.models.server import Server
from app.schemas.metric import MetricPayload
from app.services import alert_engine, metric_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["metrics"])


@router.post("/metrics", status_code=202)
async def receive_metrics(
    payload: MetricPayload,
    background_tasks: BackgroundTasks,
    server: Server = Depends(verify_agent_api_key),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Agent'tan metrik alır, DB'ye yazar ve eşik kontrolünü tetikler.

    1. Sunucu durumunu active yap
    2. Metrik kaydını yaz
    3. Servis durumlarını güncelle
    4. Log entry'lerini kaydet
    5. Eşik kontrolü — background task (response'u yavaşlatmaz)
    """
    await metric_service.update_server_status(db, server.id)
    await metric_service.save_metric(db, server.id, payload)
    await metric_service.update_services(db, server.id, payload.services)
    await metric_service.save_logs(db, server.id, payload.log_entries)

    background_tasks.add_task(alert_engine.check_thresholds, db, server.id, payload)

    return {
        "data": {"status": "accepted"},
        "meta": {"timestamp": datetime.now(UTC).isoformat()},
    }
