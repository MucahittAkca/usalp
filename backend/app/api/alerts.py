"""Alert endpoint'leri — listeleme, çözümleme ve istatistik."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.schemas.alert import AlertOut
from app.services import alert_service
from app.services.alert_service import AlertFilters

router = APIRouter(tags=["alerts"])


@router.get("/alerts")
async def list_alerts(
    server_id: int | None = Query(default=None, description="Sunucu ID filtresi"),
    severity: str | None = Query(default=None, description="Severity filtresi (warning, critical)"),
    alert_type: str | None = Query(default=None, description="Alert tipi filtresi"),
    resolved: bool | None = Query(default=None, description="Çözümleme durumu filtresi"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
) -> dict:
    """Tüm alert'leri filtreli ve sayfalı listeler."""
    filters = AlertFilters(
        server_id=server_id,
        severity=severity,
        alert_type=alert_type,
        resolved=resolved,
    )
    alerts, total = await alert_service.list_alerts(
        db, filters, page=page, per_page=per_page,
    )

    return {
        "data": [AlertOut.model_validate(a).model_dump() for a in alerts],
        "meta": {"total": total, "page": page, "per_page": per_page},
    }


@router.patch("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
) -> dict:
    """Alert'i çözüldü olarak işaretler."""
    alert = await alert_service.resolve_alert(db, alert_id)

    return {
        "data": AlertOut.model_validate(alert).model_dump(),
        "meta": {"timestamp": datetime.now(UTC).isoformat()},
    }


@router.get("/alerts/stats")
async def alert_stats(
    server_id: int | None = Query(default=None, description="Sunucu bazlı filtreleme"),
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
) -> dict:
    """Aktif alert istatistiklerini döndürür (total_active, critical, warning)."""
    stats = await alert_service.get_stats(db, server_id=server_id)

    return {
        "data": stats,
        "meta": {"timestamp": datetime.now(UTC).isoformat()},
    }
