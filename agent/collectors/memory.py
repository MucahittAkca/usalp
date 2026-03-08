"""RAM metrik toplayıcı."""

from __future__ import annotations

import psutil


def collect() -> dict:
    """RAM kullanım yüzdesini döndürür."""
    mem = psutil.virtual_memory()
    return {"ram_percent": mem.percent}
