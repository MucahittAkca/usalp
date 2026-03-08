"""Alarm motoru — metrik eşik kontrolü ve alert üretimi."""

from __future__ import annotations

import logging

from app.config import settings

logger = logging.getLogger(__name__)


def check_thresholds(cpu: float, ram: float, disk: float) -> list[dict]:
    """Metrik değerlerini eşiklerle karşılaştırır, aşım varsa alert listesi döndürür."""
    alerts: list[dict] = []

    if cpu >= settings.ALERT_CPU_CRITICAL:
        alerts.append({"type": "cpu", "severity": "critical", "message": f"CPU %{cpu:.1f} — kritik eşik aşıldı"})
    elif cpu >= settings.ALERT_CPU_WARNING:
        alerts.append({"type": "cpu", "severity": "warning", "message": f"CPU %{cpu:.1f} — uyarı eşiği aşıldı"})

    if ram >= settings.ALERT_RAM_CRITICAL:
        alerts.append({"type": "ram", "severity": "critical", "message": f"RAM %{ram:.1f} — kritik eşik aşıldı"})
    elif ram >= settings.ALERT_RAM_WARNING:
        alerts.append({"type": "ram", "severity": "warning", "message": f"RAM %{ram:.1f} — uyarı eşiği aşıldı"})

    if disk >= settings.ALERT_DISK_CRITICAL:
        alerts.append({"type": "disk", "severity": "critical", "message": f"Disk %{disk:.1f} — kritik eşik aşıldı"})
    elif disk >= settings.ALERT_DISK_WARNING:
        alerts.append({"type": "disk", "severity": "warning", "message": f"Disk %{disk:.1f} — uyarı eşiği aşıldı"})

    return alerts
