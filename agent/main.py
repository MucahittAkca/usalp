"""Usalp Agent — Sunucu metriklerini toplar ve merkezi sisteme gönderir.

``schedule`` kütüphanesi ile iki döngü çalıştırır:
- **fast_cycle** (varsayılan 30 s): CPU, RAM, Network, Servis, Log
- **slow_cycle** (varsayılan 60 s): Disk, Process

Her fast_cycle sonunda tüm veriler tek bir ``MetricPayload`` olarak
Backend API'ye gönderilir.  slow_cycle yalnızca ağır collector'ları
çalıştırıp sonuçları önbelleğe alır.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import schedule
import structlog

from collectors import cpu, disk, memory, network, process, services
from config import AgentConfig, LogFileConfig, load_config
from models import MetricPayload
from readers.log_reader import read_logs
from sender.disk_queue import enqueue_and_flush

log = structlog.get_logger()

_cached_disks: list = []
_cached_processes: list = []


def _slow_cycle(config: AgentConfig) -> None:
    """Disk ve process verilerini toplar, modül önbelleğine yazar."""
    global _cached_disks, _cached_processes  # noqa: PLW0603

    try:
        _cached_disks = disk.collect()
    except Exception:
        log.exception("collector_failed", collector="disk")

    try:
        _cached_processes = process.collect()
    except Exception:
        log.exception("collector_failed", collector="process")

    log.debug(
        "slow_cycle_done",
        disks=len(_cached_disks),
        processes=len(_cached_processes),
    )


def _fast_cycle(config: AgentConfig) -> None:
    """CPU, RAM, Network, Servis, Log toplar ve payload'ı gönderir."""
    try:
        cpu_metrics = cpu.collect()
    except Exception:
        log.exception("collector_failed", collector="cpu")
        return

    try:
        mem_metrics = memory.collect()
    except Exception:
        log.exception("collector_failed", collector="memory")
        return

    try:
        net_metrics = network.collect()
    except Exception:
        log.exception("collector_failed", collector="network")
        net_metrics = []

    try:
        svc_statuses = services.collect(config.services)
    except Exception:
        log.exception("collector_failed", collector="services")
        svc_statuses = []

    try:
        log_cfgs = [
            LogFileConfig(
                path=lf.path,
                tail_lines=lf.tail_lines,
                min_level=lf.min_level,
            )
            for lf in config.log_files
        ]
        log_entries = read_logs(log_cfgs)
    except Exception:
        log.exception("collector_failed", collector="log_reader")
        log_entries = []

    payload = MetricPayload(
        server_id=config.server_id,
        cpu=cpu_metrics,
        memory=mem_metrics,
        disks=_cached_disks,
        networks=net_metrics,
        top_processes=_cached_processes,
        services=svc_statuses,
        log_entries=log_entries,
    )

    try:
        flushed = enqueue_and_flush(payload, config)
    except Exception:
        log.exception("queue_persist_or_flush_failed", server_id=config.server_id)
        return

    if not flushed:
        log.warning("queue_flush_incomplete", server_id=config.server_id)


def main() -> None:
    """CLI giriş noktası."""
    parser = argparse.ArgumentParser(description="Usalp Monitoring Agent")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("agent.yaml"),
        help="Konfigürasyon dosyası yolu",
    )
    args = parser.parse_args()

    config = load_config(args.config)

    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(
            structlog.get_level_from_env("LOG_LEVEL", default="INFO")
        ),
    )

    log.info(
        "agent_starting",
        server_id=config.server_id,
        backend_url=config.backend_url,
        fast_interval=config.intervals.fast,
        slow_interval=config.intervals.slow,
        queue_dir=config.queue.dir,
    )

    _slow_cycle(config)

    schedule.every(config.intervals.fast).seconds.do(_fast_cycle, config=config)
    schedule.every(config.intervals.slow).seconds.do(_slow_cycle, config=config)

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
