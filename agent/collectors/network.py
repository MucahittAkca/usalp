"""Ağ arayüzü trafik ve hata istatistikleri toplayıcı.

Her fiziksel arayüz için saniye başına gönderilen/alınan byte ve
paket miktarını hesaplar.  Loopback (``lo``) arayüzü filtrelenir.

Rate hesabı için bir önceki ölçüm modül seviyesinde saklanır;
ilk çağrıda rate değerleri 0.0 döner.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import NamedTuple

import psutil

from models import NetworkMetrics

_IGNORED_INTERFACES = frozenset({"lo"})


class _Snapshot(NamedTuple):
    bytes_sent: int
    bytes_recv: int
    packets_sent: int
    packets_recv: int


@dataclass
class _PreviousNet:
    timestamp: float = 0.0
    counters: dict[str, _Snapshot] = field(default_factory=dict)


_prev_net = _PreviousNet()


def collect() -> list[NetworkMetrics]:
    """Tüm fiziksel ağ arayüzlerinin trafik metriklerini toplar."""
    now = time.monotonic()
    per_nic = psutil.net_io_counters(pernic=True) or {}

    elapsed = now - _prev_net.timestamp if _prev_net.timestamp else 0.0

    results: list[NetworkMetrics] = []

    for iface, counters in per_nic.items():
        if iface in _IGNORED_INTERFACES:
            continue

        cur = _Snapshot(
            bytes_sent=counters.bytes_sent,
            bytes_recv=counters.bytes_recv,
            packets_sent=counters.packets_sent,
            packets_recv=counters.packets_recv,
        )

        bytes_sent_rate = 0.0
        bytes_recv_rate = 0.0
        packets_sent_rate = 0.0
        packets_recv_rate = 0.0

        if elapsed > 0 and iface in _prev_net.counters:
            prev = _prev_net.counters[iface]
            bytes_sent_rate = max(0.0, (cur.bytes_sent - prev.bytes_sent) / elapsed)
            bytes_recv_rate = max(0.0, (cur.bytes_recv - prev.bytes_recv) / elapsed)
            packets_sent_rate = max(0.0, (cur.packets_sent - prev.packets_sent) / elapsed)
            packets_recv_rate = max(0.0, (cur.packets_recv - prev.packets_recv) / elapsed)

        _prev_net.counters[iface] = cur

        results.append(
            NetworkMetrics(
                interface=iface,
                bytes_sent_per_sec=round(bytes_sent_rate, 2),
                bytes_recv_per_sec=round(bytes_recv_rate, 2),
                packets_sent_per_sec=round(packets_sent_rate, 2),
                packets_recv_per_sec=round(packets_recv_rate, 2),
                errors_in=counters.errin,
                errors_out=counters.errout,
            )
        )

    _prev_net.timestamp = now
    return results
