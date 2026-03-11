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


async def _active_alert_exists(
    db: AsyncSession, server_id: int, alert_type: str,
) -> bool:
    """Aynı tipte çözülmemiş alert var mı kontrol eder (spam önleme)."""
    stmt = (
        select(Alert.id)
        .where(
            Alert.server_id == server_id,
            Alert.type == alert_type,
            Alert.resolved_at.is_(None),
        )
        .limit(1)
    )
    return await db.scalar(stmt) is not None


async def _create_alert_if_not_exists(
    db: AsyncSession,
    server_id: int,
    *,
    alert_type: str,
    severity: str,
    message: str,
) -> Alert | None:
    """Aynı tipte aktif alert yoksa yeni alert oluşturur."""
    if await _active_alert_exists(db, server_id, alert_type):
        return None

    alert = Alert(
        server_id=server_id,
        type=alert_type,
        severity=severity,
        message=message,
    )
    db.add(alert)
    await db.flush()
    logger.warning("Alert oluşturuldu: server=%d type=%s severity=%s", server_id, alert_type, severity)
    return alert


def _build_context(server_id: int, payload: MetricPayload, focus: str) -> str:
    """AI analizi için bağlam metni oluşturur."""
    lines = [
        f"Server ID: {server_id}",
        f"Collected at: {payload.collected_at.isoformat()}",
        f"Focus: {focus}",
        f"CPU: {payload.cpu.percent:.1f}%  (load 1/5/15: "
        f"{payload.cpu.load_avg_1:.2f}/{payload.cpu.load_avg_5:.2f}/{payload.cpu.load_avg_15:.2f})",
        f"Memory: {payload.memory.percent:.1f}%",
    ]
    for d in payload.disks:
        lines.append(f"Disk {d.path}: {d.percent:.1f}%")
    for svc in payload.services:
        lines.append(f"Service {svc.name}: {svc.status}")
    error_logs = [le for le in payload.log_entries if le.level in ("CRITICAL", "ERROR")]
    for le in error_logs[:10]:
        lines.append(f"[{le.level}] {le.source_file}: {le.message}")
    return "\n".join(lines)


async def _maybe_trigger_ai(
    db: AsyncSession,
    alert: Alert | None,
    server_id: int,
    payload: MetricPayload,
    focus: str,
) -> None:
    """Yeni kritik alert oluşturulduysa AI analiz tetikler."""
    if alert is None or alert.severity != "critical":
        return
    try:
        context = _build_context(server_id, payload, focus)
        await ai_analyzer.trigger_analysis(
            db, server_id, context, alert_id=alert.id,
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
        a = await _create_alert_if_not_exists(
            db, server_id,
            alert_type="cpu_threshold", severity="critical",
            message=f"CPU kullanımı kritik: %{cpu:.1f}",
        )
        if a:
            created.append(a)
        await _maybe_trigger_ai(db, a, server_id, payload, f"CPU kritik: %{cpu:.1f}")
    elif cpu >= THRESHOLDS["cpu_percent"]["warning"]:
        a = await _create_alert_if_not_exists(
            db, server_id,
            alert_type="cpu_threshold", severity="warning",
            message=f"CPU kullanımı yüksek: %{cpu:.1f}",
        )
        if a:
            created.append(a)
    else:
        await alert_service.auto_resolve_by_type(db, server_id, "cpu_threshold")

    # --- RAM ---
    ram = payload.memory.percent
    if ram >= THRESHOLDS["ram_percent"]["critical"]:
        a = await _create_alert_if_not_exists(
            db, server_id,
            alert_type="ram_threshold", severity="critical",
            message=f"RAM kullanımı kritik: %{ram:.1f}",
        )
        if a:
            created.append(a)
        await _maybe_trigger_ai(db, a, server_id, payload, f"RAM kritik: %{ram:.1f}")
    elif ram >= THRESHOLDS["ram_percent"]["warning"]:
        a = await _create_alert_if_not_exists(
            db, server_id,
            alert_type="ram_threshold", severity="warning",
            message=f"RAM kullanımı yüksek: %{ram:.1f}",
        )
        if a:
            created.append(a)
    else:
        await alert_service.auto_resolve_by_type(db, server_id, "ram_threshold")

    # --- Disk ---
    max_disk = max((d.percent for d in payload.disks), default=0.0)
    if max_disk >= THRESHOLDS["disk_percent"]["critical"]:
        a = await _create_alert_if_not_exists(
            db, server_id,
            alert_type="disk_threshold", severity="critical",
            message=f"Disk kullanımı kritik: %{max_disk:.1f}",
        )
        if a:
            created.append(a)
        await _maybe_trigger_ai(db, a, server_id, payload, f"Disk kritik: %{max_disk:.1f}")
    elif max_disk >= THRESHOLDS["disk_percent"]["warning"]:
        a = await _create_alert_if_not_exists(
            db, server_id,
            alert_type="disk_threshold", severity="warning",
            message=f"Disk kullanımı yüksek: %{max_disk:.1f}",
        )
        if a:
            created.append(a)
    else:
        await alert_service.auto_resolve_by_type(db, server_id, "disk_threshold")

    # --- Failed servisler ---
    for svc in payload.services:
        if svc.status == "failed":
            a = await _create_alert_if_not_exists(
                db, server_id,
                alert_type="service_failed", severity="critical",
                message=f"Servis durumu: {svc.name} failed",
            )
            if a:
                created.append(a)
            await _maybe_trigger_ai(
                db, a, server_id, payload, f"Servis failed: {svc.name}",
            )

    # --- Kritik log patlaması (5+ ERROR/CRITICAL) ---
    critical_logs = [le for le in payload.log_entries if le.level in ("CRITICAL", "ERROR")]
    if len(critical_logs) >= 5:
        a = await _create_alert_if_not_exists(
            db, server_id,
            alert_type="critical_log_burst", severity="warning",
            message=f"{len(critical_logs)} kritik/hata logu tespit edildi",
        )
        if a:
            created.append(a)

    return created
