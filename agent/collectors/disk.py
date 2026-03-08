"""Disk metrik toplayıcı."""

from __future__ import annotations

import psutil


def collect() -> dict:
    """Kök disk kullanım yüzdesini döndürür."""
    usage = psutil.disk_usage("/")
    return {"disk_percent": usage.percent}
