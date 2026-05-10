"""En çok kaynak tüketen işlemlerin toplayıcısı.

CPU kullanımına göre sıralayarak ilk 10 işlemi döndürür.
``psutil.process_iter`` cache mekanizması sayesinde ikinci
çağrıdan itibaren doğru CPU yüzdeleri hesaplanır; ilk çağrıda
kısa bir bekleme ile iki ölçüm alınır.
"""

from __future__ import annotations

import time

import psutil

from models import ProcessInfo

_TOP_N = 10
_PRIME_INTERVAL = 0.1


def collect() -> list[ProcessInfo]:
    """CPU kullanımına göre en yoğun ``_TOP_N`` işlemi toplar."""
    attrs = ["pid", "name", "cpu_percent", "memory_percent", "status"]

    # İlk geçiş: cpu_percent sayaçlarını başlat (ilk çağrıda 0.0 döner)
    for _proc in psutil.process_iter(attrs):
        pass

    time.sleep(_PRIME_INTERVAL)

    processes: list[ProcessInfo] = []
    for proc in psutil.process_iter(attrs):
        try:
            info = proc.info  # type: ignore[attr-defined]
            processes.append(
                ProcessInfo(
                    pid=info["pid"],
                    name=info["name"] or "",
                    cpu_percent=info["cpu_percent"] or 0.0,
                    memory_percent=round(info["memory_percent"] or 0.0, 2),
                    status=info["status"] or "unknown",
                )
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    processes.sort(key=lambda p: p.cpu_percent, reverse=True)
    return processes[:_TOP_N]
