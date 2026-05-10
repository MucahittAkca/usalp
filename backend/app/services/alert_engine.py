"""Alarm motoru — metrik eşik kontrolü, alert üretimi ve kritik durumlarda AI tetikleme."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.alert import Alert
from app.schemas.metric import MetricPayload
from app.services import ai_analyzer, alert_service

logger = logging.getLogger(__name__)

THRESHOLDS: dict[str, dict[str, float]] = {
    "cpu_percent": {"warning": settings.ALERT_CPU_WARNING, "critical": settings.ALERT_CPU_CRITICAL},
    "ram_percent": {"warning": settings.ALERT_RAM_WARNING, "critical": settings.ALERT_RAM_CRITICAL},
    "disk_percent": {
        "warning": settings.ALERT_DISK_WARNING,
        "critical": settings.ALERT_DISK_CRITICAL,
    },
}

ALERT_TYPES = {
    "cpu_threshold",
    "ram_threshold",
    "disk_threshold",
    "service_failed",
    "critical_log_burst",
}


async def _get_active_alert(
    db: AsyncSession,
    server_id: int,
    dedupe_key: str,
) -> Alert | None:
    """Aktif alert'i dedupe key ile getirir."""
    stmt = (
        select(Alert)
        .where(
            Alert.server_id == server_id,
            Alert.dedupe_key == dedupe_key,
            Alert.resolved_at.is_(None),
        )
        .limit(1)
    )
    return await db.scalar(stmt)


async def _upsert_alert(
    db: AsyncSession,
    server_id: int,
    *,
    alert_type: str,
    dedupe_key: str,
    severity: str,
    message: str,
) -> tuple[Alert | None, bool]:
    """Aktif alert yoksa oluşturur; varsa severity/message günceller.

    İkinci dönüş değeri, alert'in bu çağrıda ilk kez kritik hale gelip
    AI tetikleme hakkı kazanıp kazanmadığını belirtir.
    """
    existing = await _get_active_alert(db, server_id, dedupe_key)
    if existing:
        was_critical = existing.severity == "critical"
        changed = existing.severity != severity or existing.message != message
        if changed:
            existing.severity = severity
            existing.message = message
            await db.flush()
        return existing if changed else None, severity == "critical" and not was_critical

    alert = Alert(
        server_id=server_id,
        type=alert_type,
        dedupe_key=dedupe_key,
        severity=severity,
        message=message,
    )
    db.add(alert)
    await db.flush()
    logger.warning("Alert oluşturuldu: server=%d type=%s severity=%s", server_id, alert_type, severity)
    return alert, severity == "critical"


async def _maybe_trigger_ai(
    db: AsyncSession,
    alert: Alert | None,
    server_id: int,
    *,
    should_trigger: bool = True,
) -> None:
    """Yeni kritik alert oluşturulduysa AI analiz tetikler.

    Bağlam paketi artık ai_analyzer içinde DB'den çekilir.
    """
    if alert is None or alert.severity != "critical" or not should_trigger:
        return
    try:
        await ai_analyzer.trigger_analysis(
            db, server_id, alert_id=alert.id,
        )
    except Exception:
        logger.exception("AI analiz tetiklenemedi: server=%d alert=%d", server_id, alert.id)


async def check_thresholds(
    db: AsyncSession, server_id: int, payload: MetricPayload,
) -> list[Alert]:
    """Tüm metrikleri eşiklerle karşılaştırır, gerekli alert'leri üretir.

    Eşik altına düşen metrikler için mevcut alert'leri otomatik çözümler.
    """
    created: list[Alert] = []

    # --- CPU ---
    cpu = payload.cpu.percent
    if cpu >= THRESHOLDS["cpu_percent"]["critical"]:
        a, should_trigger = await _upsert_alert(
            db, server_id,
            alert_type="cpu_threshold", dedupe_key="cpu_threshold", severity="critical",
            message=f"CPU kullanımı kritik: %{cpu:.1f}",
        )
        if a:
            created.append(a)
        await _maybe_trigger_ai(db, a, server_id, should_trigger=should_trigger)
    elif cpu >= THRESHOLDS["cpu_percent"]["warning"]:
        a, _ = await _upsert_alert(
            db, server_id,
            alert_type="cpu_threshold", dedupe_key="cpu_threshold", severity="warning",
            message=f"CPU kullanımı yüksek: %{cpu:.1f}",
        )
        if a:
            created.append(a)
    else:
        await alert_service.auto_resolve_by_dedupe_key(db, server_id, "cpu_threshold")

    # --- RAM ---
    ram = payload.memory.percent
    if ram >= THRESHOLDS["ram_percent"]["critical"]:
        a, should_trigger = await _upsert_alert(
            db, server_id,
            alert_type="ram_threshold", dedupe_key="ram_threshold", severity="critical",
            message=f"RAM kullanımı kritik: %{ram:.1f}",
        )
        if a:
            created.append(a)
        await _maybe_trigger_ai(db, a, server_id, should_trigger=should_trigger)
    elif ram >= THRESHOLDS["ram_percent"]["warning"]:
        a, _ = await _upsert_alert(
            db, server_id,
            alert_type="ram_threshold", dedupe_key="ram_threshold", severity="warning",
            message=f"RAM kullanımı yüksek: %{ram:.1f}",
        )
        if a:
            created.append(a)
    else:
        await alert_service.auto_resolve_by_dedupe_key(db, server_id, "ram_threshold")

    # --- Disk ---
    max_disk = max((d.percent for d in payload.disks), default=0.0)
    if max_disk >= THRESHOLDS["disk_percent"]["critical"]:
        a, should_trigger = await _upsert_alert(
            db, server_id,
            alert_type="disk_threshold", dedupe_key="disk_threshold", severity="critical",
            message=f"Disk kullanımı kritik: %{max_disk:.1f}",
        )
        if a:
            created.append(a)
        await _maybe_trigger_ai(db, a, server_id, should_trigger=should_trigger)
    elif max_disk >= THRESHOLDS["disk_percent"]["warning"]:
        a, _ = await _upsert_alert(
            db, server_id,
            alert_type="disk_threshold", dedupe_key="disk_threshold", severity="warning",
            message=f"Disk kullanımı yüksek: %{max_disk:.1f}",
        )
        if a:
            created.append(a)
    else:
        await alert_service.auto_resolve_by_dedupe_key(db, server_id, "disk_threshold")

    # --- Failed servisler ---
    failed_service_keys: set[str] = set()
    for svc in payload.services:
        if svc.status == "failed":
            dedupe_key = f"service_failed:{svc.name}"
            failed_service_keys.add(dedupe_key)
            a, should_trigger = await _upsert_alert(
                db, server_id,
                alert_type="service_failed", dedupe_key=dedupe_key, severity="critical",
                message=f"Servis durumu: {svc.name} failed",
            )
            if a:
                created.append(a)
            await _maybe_trigger_ai(db, a, server_id, should_trigger=should_trigger)
    await alert_service.auto_resolve_missing_dedupe_keys(
        db, server_id, "service_failed", failed_service_keys,
    )

    # --- Kritik log patlaması (5+ ERROR/CRITICAL) ---
    critical_logs = [le for le in payload.log_entries if le.level in ("CRITICAL", "ERROR")]
    if len(critical_logs) >= 5:
        a, _ = await _upsert_alert(
            db, server_id,
            alert_type="critical_log_burst",
            dedupe_key="critical_log_burst",
            severity="warning",
            message=f"{len(critical_logs)} kritik/hata logu tespit edildi",
        )
        if a:
            created.append(a)
    else:
        await alert_service.auto_resolve_by_dedupe_key(
            db, server_id, "critical_log_burst",
        )

    await alert_service.sync_server_status_from_alerts(db, server_id)
    return created
