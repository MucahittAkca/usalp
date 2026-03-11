"""CPU metrik toplayıcı.

psutil ile toplam/çekirdek bazında CPU kullanım yüzdesini
ve 1/5/15 dakikalık load average değerlerini toplar.
"""

from __future__ import annotations

import psutil

from agent.models import CpuMetrics


def collect() -> CpuMetrics:
    """Anlık CPU metriklerini toplar ve ``CpuMetrics`` modeli döndürür.

    ``cpu_percent(interval=1)`` çağrısı 1 saniyelik örnekleme yapar;
    ``interval=None`` kullanılmaz çünkü ilk çağrıda anlamsız sonuç verir.
    """
    percent = psutil.cpu_percent(interval=1)
    per_core = psutil.cpu_percent(percpu=True)
    load_1, load_5, load_15 = psutil.getloadavg()

    return CpuMetrics(
        percent=percent,
        per_core=per_core,
        load_avg_1=load_1,
        load_avg_5=load_5,
        load_avg_15=load_15,
    )
