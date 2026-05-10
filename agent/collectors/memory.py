"""RAM ve swap bellek metrik toplayıcı.

psutil ile fiziksel bellek (RAM) ve swap alanı kullanım
bilgilerini byte cinsinden toplar.
"""

from __future__ import annotations

import psutil

from models import MemoryMetrics


def collect() -> MemoryMetrics:
    """Anlık bellek metriklerini toplar ve ``MemoryMetrics`` modeli döndürür."""
    vm = psutil.virtual_memory()
    swap = psutil.swap_memory()

    return MemoryMetrics(
        total_bytes=vm.total,
        used_bytes=vm.used,
        available_bytes=vm.available,
        cached_bytes=vm.cached,
        percent=vm.percent,
        swap_total_bytes=swap.total,
        swap_used_bytes=swap.used,
    )
