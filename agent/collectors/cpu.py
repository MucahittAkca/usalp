"""CPU metrik toplayıcı."""

from __future__ import annotations

import os

import psutil


def collect() -> dict:
    """CPU kullanım yüzdesini döndürür."""
    return {"cpu_percent": psutil.cpu_percent(interval=1)}


def collect_load_avg() -> tuple[float, float, float]:
    """1, 5 ve 15 dakikalık load average değerlerini döndürür."""
    return os.getloadavg()
