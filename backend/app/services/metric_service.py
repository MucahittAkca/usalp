"""Metrik kaydetme, servis güncelleme, log yazma ve sunucu durum takibi."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.log_entry import LogEntry
from app.models.metric import Metric
from app.models.server import Server
from app.models.service_status import ServiceStatus
from app.schemas.metric import LogData, MetricPayload, ServiceData

logger = logging.getLogger(__name__)

MAX_LOG_ENTRIES_PER_BATCH = 200


async def update_server_status(db: AsyncSession, server_id: int) -> None:
    """Metrik geldiğinde sunucuyu online olarak işaretler ve last_seen günceller."""
    await db.execute(
        update(Server)
        .where(Server.id == server_id)
        .values(status="online", last_seen=datetime.now(UTC))
    )


async def save_metric(db: AsyncSession, server_id: int, payload: MetricPayload) -> Metric:
    """Payload'dan özet metrikleri çıkarıp tek satır olarak DB'ye yazar."""
    max_disk = max((d.percent for d in payload.disks), default=0.0)
    total_net_in = sum(n.bytes_recv_per_sec for n in payload.networks)
    total_net_out = sum(n.bytes_sent_per_sec for n in payload.networks)

    metric = Metric(
        server_id=server_id,
        cpu_percent=payload.cpu.percent,
        ram_percent=payload.memory.percent,
        disk_percent=max_disk,
        network_in_bytes=int(total_net_in),
        network_out_bytes=int(total_net_out),
        load_avg_1=payload.cpu.load_avg_1,
        load_avg_5=payload.cpu.load_avg_5,
        load_avg_15=payload.cpu.load_avg_15,
        raw_json=payload.model_dump(mode="json"),
        recorded_at=payload.collected_at,
    )
    db.add(metric)
    await db.flush()
    logger.info("Metrik kaydedildi: server_id=%d cpu=%.1f%%", server_id, payload.cpu.percent)
    return metric


async def update_services(
    db: AsyncSession,
    server_id: int,
    services: Sequence[ServiceData],
) -> list[ServiceStatus]:
    """Servis durumlarını yeni snapshot olarak kaydeder."""
    records: list[ServiceStatus] = []
    for svc in services:
        record = ServiceStatus(
            server_id=server_id,
            service_name=svc.name,
            status=svc.status,
        )
        db.add(record)
        records.append(record)
    if records:
        await db.flush()
    return records


async def save_logs(
    db: AsyncSession,
    server_id: int,
    logs: Sequence[LogData],
) -> int:
    """Log entry'lerini toplu olarak DB'ye yazar. Max 200 satır (payload boyut kontrolü)."""
    trimmed = logs[:MAX_LOG_ENTRIES_PER_BATCH]
    count = 0
    for entry in trimmed:
        exists = await db.scalar(
            select(LogEntry.id)
            .where(
                LogEntry.server_id == server_id,
                LogEntry.source_file == entry.source_file,
                LogEntry.raw_line == entry.raw_line,
                LogEntry.logged_at == entry.logged_at,
            )
            .limit(1)
        )
        if exists:
            continue
        record = LogEntry(
            server_id=server_id,
            source_file=entry.source_file,
            level=entry.level,
            message=entry.message,
            raw_line=entry.raw_line,
            logged_at=entry.logged_at,
        )
        db.add(record)
        count += 1
    if count:
        await db.flush()
    if len(logs) > MAX_LOG_ENTRIES_PER_BATCH:
        logger.warning(
            "Log limiti aşıldı: server_id=%d gelen=%d yazılan=%d",
            server_id, len(logs), count,
        )
    return count
