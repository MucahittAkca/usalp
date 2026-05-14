"""Metrik endpoint'leri — Agent'tan veri alımı."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import verify_agent_api_key
from app.database import get_db
from app.models.server import Server
from app.schemas.metric import MetricOut, MetricPayload
from app.services import alert_engine, alert_notifications, metric_service, metric_stream

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

    1. Sunucu durumunu online yap
    2. Metrik kaydını yaz
    3. Servis durumlarını güncelle
    4. Log entry'lerini kaydet
    5. Eşik kontrolü — background task (response'u yavaşlatmaz)
    """
    await metric_service.update_server_status(db, server.id)
    metric = await metric_service.save_metric(db, server.id, payload)
    await metric_service.update_services(db, server.id, payload.services)
    await metric_service.save_logs(db, server.id, payload.log_entries)
    created_alerts = await alert_engine.check_thresholds(db, server.id, payload)
    await db.commit()
    notifications = alert_notifications.build_alert_notifications(created_alerts, server)
    if notifications:
        background_tasks.add_task(alert_notifications.notify_alerts, notifications)
    await metric_stream.hub.publish(server.id, MetricOut.model_validate(metric))

    return {
        "data": {"status": "accepted", "alerts_changed": len(created_alerts)},
        "meta": {"timestamp": datetime.now(UTC).isoformat()},
    }
