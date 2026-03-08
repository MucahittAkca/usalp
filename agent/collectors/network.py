"""Ağ metrik toplayıcı."""

from __future__ import annotations

import psutil


def collect() -> dict:
    """Toplam ağ giriş/çıkış baytlarını döndürür."""
    counters = psutil.net_io_counters()
    return {
        "network_in_bytes": counters.bytes_recv,
        "network_out_bytes": counters.bytes_sent,
    }
