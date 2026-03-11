"""Disk kullanım ve I/O hızı toplayıcı.

Her gerçek mount-point için alan kullanımını ve saniye başına
okuma/yazma byte miktarını hesaplar.  Sanal dosya sistemleri
(tmpfs, devtmpfs, squashfs) filtrelenir.

I/O rate hesabı için bir önceki ölçüm modül seviyesinde saklanır;
ilk çağrıda rate değerleri 0.0 döner.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import psutil

from agent.models import DiskMetrics

_VIRTUAL_FS_TYPES = frozenset({"tmpfs", "devtmpfs", "squashfs"})


@dataclass
class _PreviousIO:
    timestamp: float = 0.0
    counters: dict[str, tuple[int, int]] = field(default_factory=dict)


_prev_io = _PreviousIO()


def _device_key(device_path: str) -> str:
    """``/dev/sda1`` → ``sda1`` dönüşümü yapar."""
    return device_path.rsplit("/", 1)[-1]


def collect() -> list[DiskMetrics]:
    """Tüm gerçek disk bölümlerinin kullanım ve I/O metriklerini toplar."""
    now = time.monotonic()
    partitions = psutil.disk_partitions(all=False)

    io_counters = psutil.disk_io_counters(perdisk=True) or {}

    elapsed = now - _prev_io.timestamp if _prev_io.timestamp else 0.0

    results: list[DiskMetrics] = []

    for part in partitions:
        if part.fstype in _VIRTUAL_FS_TYPES:
            continue

        try:
            usage = psutil.disk_usage(part.mountpoint)
        except PermissionError:
            continue

        dk = _device_key(part.device)
        read_rate = 0.0
        write_rate = 0.0

        if dk in io_counters:
            cur_read = io_counters[dk].read_bytes
            cur_write = io_counters[dk].write_bytes

            if elapsed > 0 and dk in _prev_io.counters:
                prev_read, prev_write = _prev_io.counters[dk]
                read_rate = max(0.0, (cur_read - prev_read) / elapsed)
                write_rate = max(0.0, (cur_write - prev_write) / elapsed)

            _prev_io.counters[dk] = (cur_read, cur_write)

        results.append(
            DiskMetrics(
                path=part.mountpoint,
                total_bytes=usage.total,
                used_bytes=usage.used,
                free_bytes=usage.free,
                percent=usage.percent,
                read_bytes_per_sec=round(read_rate, 2),
                write_bytes_per_sec=round(write_rate, 2),
            )
        )

    _prev_io.timestamp = now
    return results
