"""Alert endpoint'leri."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["alerts"])


@router.get("/alerts")
async def list_alerts() -> dict:
    """Tüm alert'leri listeler."""
    # TODO(v1): DB'den alert listesi
    return {"data": [], "meta": {"total": 0, "page": 1, "per_page": 20}}


@router.patch("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: int) -> dict:
    """Alert'i çözüldü olarak işaretler."""
    # TODO(v1): Alert resolved_at güncelle
    return {"data": {"id": alert_id, "resolved": True}, "meta": {"timestamp": ""}}
