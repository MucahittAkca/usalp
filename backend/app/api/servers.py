"""Sunucu endpoint'leri — liste, detay, metrik/servis/log sorguları."""

from __future__ import annotations

import asyncio
import json
import secrets
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from app.api.deps import get_current_user
from app.core.exceptions import NotFoundError
from app.core.time import as_naive_utc, utc_now_naive
from app.database import async_session, get_db
from app.models.log_entry import LogEntry
from app.models.metric import Metric
from app.models.server import Server
from app.models.service_status import ServiceStatus
from app.schemas.metric import MetricOut
from app.schemas.server import (
    LogEntryOut,
    ServerApiKeyOut,
    ServerCreate,
    ServerCreatedOut,
    ServerOut,
    ServiceStatusOut,
    normalize_tags,
)
from app.services import metric_stream, server_status

router = APIRouter(tags=["servers"])
STREAM_KEEPALIVE_SECONDS = 15


def _generate_api_key() -> str:
    """Agent için tek kullanımlık API anahtarı üretir."""
    return f"usalp-{secrets.token_hex(16)}"


def _normalize_optional_filter(value: str | None) -> str | None:
    """Boş string filtreleri yok sayar, dolu değerleri normalize eder."""
    if value is None:
        return None
    normalized = value.strip().lower()
    return normalized or None


async def _get_server_or_404(db: AsyncSession, server_id: int) -> Server:
    """Server'ı ID ile bulur, yoksa 404 fırlatır."""
    server = await db.get(Server, server_id)
    if not server:
        raise NotFoundError("Server", server_id)
    return server


def _sse_event(event: str, data: dict[str, object]) -> str:
    """Bir SSE mesajını text/event-stream formatına çevirir."""
    payload = json.dumps(data, separators=(",", ":"))
    return f"event: {event}\ndata: {payload}\n\n"


async def _metric_stream_events(
    server_id: int,
    queue: asyncio.Queue[MetricOut],
) -> AsyncGenerator[str, None]:
    """Yeni metrikleri SSE mesajları olarak üretir."""
    try:
        yield _sse_event("ready", {"server_id": server_id})
        while True:
            try:
                metric = await asyncio.wait_for(
                    queue.get(),
                    timeout=STREAM_KEEPALIVE_SECONDS,
                )
            except TimeoutError:
                yield ": keepalive\n\n"
                continue

            yield _sse_event("metric", metric.model_dump(mode="json"))
    finally:
        await metric_stream.hub.unsubscribe(server_id, queue)


# ---- POST /servers ----


@router.post("/servers", status_code=201)
async def create_server(
    body: ServerCreate,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
) -> dict:
    """Yeni sunucu kaydı oluşturur ve api_key döndürür.

    api_key yalnızca bu yanıtta görünür — sonradan sorgulanamaz.
    """
    api_key = _generate_api_key()
    server = Server(
        name=body.name,
        hostname=body.hostname,
        ip_address=body.ip_address,
        environment=body.environment,
        group_name=body.group_name,
        tags=body.tags,
        api_key=api_key,
        status="offline",
    )
    db.add(server)
    await db.flush()
    await db.refresh(server)

    return {
        "data": ServerCreatedOut.model_validate(server).model_dump(),
        "meta": {"timestamp": datetime.now(UTC).isoformat()},
    }


# ---- GET /servers ----


@router.get("/servers")
async def list_servers(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    environment: str | None = Query(default=None, max_length=50, description="Ortam filtresi"),
    group_name: str | None = Query(default=None, max_length=100, description="Sunucu grubu filtresi"),
    tag: str | None = Query(default=None, max_length=40, description="Etiket filtresi"),
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
) -> dict:
    """Kayıtlı sunucuların sayfalı listesini döndürür."""
    await server_status.mark_stale_servers_offline(db)

    environment = _normalize_optional_filter(environment)
    group_name = _normalize_optional_filter(group_name)
    normalized_tags = normalize_tags([tag]) if tag else []
    tag = normalized_tags[0] if normalized_tags else None

    where_clauses = []
    if environment:
        where_clauses.append(Server.environment == environment)
    if group_name:
        where_clauses.append(Server.group_name == group_name)

    if tag:
        stmt = select(Server).where(*where_clauses).order_by(Server.created_at.desc())
        result = await db.execute(stmt)
        filtered = [server for server in result.scalars().all() if tag in (server.tags or [])]
        total = len(filtered)
        servers = filtered[(page - 1) * per_page : page * per_page]
    else:
        total = await db.scalar(select(func.count(Server.id)).where(*where_clauses))

        stmt = (
            select(Server)
            .where(*where_clauses)
            .order_by(Server.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        result = await db.execute(stmt)
        servers = result.scalars().all()

    return {
        "data": [ServerOut.model_validate(s).model_dump() for s in servers],
        "meta": {"total": total or 0, "page": page, "per_page": per_page},
    }


# ---- GET /servers/{server_id} ----


@router.get("/servers/{server_id}")
async def get_server(
    server_id: int,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
) -> dict:
    """Belirli bir sunucunun detayını döndürür."""
    await server_status.mark_stale_servers_offline(db)
    server = await _get_server_or_404(db, server_id)
    return {
        "data": ServerOut.model_validate(server).model_dump(),
        "meta": {"timestamp": datetime.now(UTC).isoformat()},
    }


# ---- POST /servers/{server_id}/rotate-key ----


@router.post("/servers/{server_id}/rotate-key")
async def rotate_server_key(
    server_id: int,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
) -> dict:
    """Sunucunun agent API anahtarını yeniler; yeni anahtar yalnızca bu yanıtta görünür."""
    server = await _get_server_or_404(db, server_id)
    server.api_key = _generate_api_key()
    server.api_key_revoked_at = None
    server.status = "offline"
    server.last_seen = None
    await db.flush()

    return {
        "data": ServerApiKeyOut(id=server.id, api_key=server.api_key).model_dump(),
        "meta": {"timestamp": datetime.now(UTC).isoformat()},
    }


# ---- PATCH /servers/{server_id}/revoke-key ----


@router.patch("/servers/{server_id}/revoke-key")
async def revoke_server_key(
    server_id: int,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
) -> dict:
    """Sunucunun mevcut agent API anahtarını iptal eder."""
    server = await _get_server_or_404(db, server_id)
    server.api_key_revoked_at = datetime.now(UTC)
    server.status = "offline"
    await db.flush()

    return {
        "data": ServerOut.model_validate(server).model_dump(),
        "meta": {"timestamp": datetime.now(UTC).isoformat()},
    }


# ---- GET /servers/{server_id}/metrics ----


@router.get("/servers/{server_id}/metrics/stream")
async def stream_server_metrics(
    server_id: int,
    _user: str = Depends(get_current_user),
) -> StreamingResponse:
    """Sunucuya ait yeni metrikleri SSE stream olarak yayınlar."""
    async with async_session() as db:
        await _get_server_or_404(db, server_id)

    queue = await metric_stream.hub.subscribe(server_id)
    return StreamingResponse(
        _metric_stream_events(server_id, queue),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/servers/{server_id}/metrics")
async def get_server_metrics(
    server_id: int,
    from_dt: datetime | None = Query(default=None, description="Başlangıç zamanı (ISO 8601)"),
    to_dt: datetime | None = Query(default=None, description="Bitiş zamanı (ISO 8601)"),
    limit: int = Query(default=100, ge=1, le=1000, description="Döndürülecek max kayıt"),
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
) -> dict:
    """Sunucuya ait metrikleri zaman aralığı filtresiyle döndürür.

    from_dt/to_dt verilmezse son 1 saati döndürür.
    raw_json performans için yüklenmez; detay için /metrics/{id} kullanılmalı.
    """
    await _get_server_or_404(db, server_id)

    now = utc_now_naive()
    from_dt = now - timedelta(hours=1) if from_dt is None else as_naive_utc(from_dt)
    to_dt = now if to_dt is None else as_naive_utc(to_dt)

    where_clauses = [
        Metric.server_id == server_id,
        Metric.recorded_at >= from_dt,
        Metric.recorded_at <= to_dt,
    ]

    total = await db.scalar(
        select(func.count(Metric.id)).where(*where_clauses)
    ) or 0

    stmt = (
        select(Metric)
        .options(defer(Metric.raw_json))
        .where(*where_clauses)
        .order_by(Metric.recorded_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    metrics = result.scalars().all()

    return {
        "data": [MetricOut.model_validate(m).model_dump() for m in metrics],
        "meta": {
            "total": total,
            "limit": limit,
            "from": from_dt.isoformat(),
            "to": to_dt.isoformat(),
        },
    }


# ---- GET /servers/{server_id}/services ----


@router.get("/servers/{server_id}/services")
async def get_server_services(
    server_id: int,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
) -> dict:
    """Sunucuya ait en son servis durumlarını döndürür (her servis için son snapshot)."""
    await _get_server_or_404(db, server_id)

    subq = (
        select(
            ServiceStatus.service_name,
            func.max(ServiceStatus.id).label("latest_id"),
        )
        .where(ServiceStatus.server_id == server_id)
        .group_by(ServiceStatus.service_name)
        .subquery()
    )
    stmt = select(ServiceStatus).join(subq, ServiceStatus.id == subq.c.latest_id)
    result = await db.execute(stmt)
    services = result.scalars().all()

    return {
        "data": [ServiceStatusOut.model_validate(s).model_dump() for s in services],
        "meta": {"timestamp": datetime.now(UTC).isoformat()},
    }


# ---- GET /servers/{server_id}/logs ----


@router.get("/servers/{server_id}/logs")
async def get_server_logs(
    server_id: int,
    level: str | None = Query(default=None, description="Log seviyesi filtresi (ERROR, WARNING vb.)"),
    q: str | None = Query(default=None, max_length=200, description="Mesaj, raw satır veya kaynak dosyada arama"),
    from_dt: datetime | None = Query(default=None, description="Başlangıç zamanı (ISO 8601)"),
    to_dt: datetime | None = Query(default=None, description="Bitiş zamanı (ISO 8601)"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
) -> dict:
    """Sunucuya ait log kayıtlarını sayfalı, seviye ve zaman filtreli döndürür.

    raw_line alanı liste yanıtında döndürülmez (LogEntryOut).
    """
    await _get_server_or_404(db, server_id)

    where_clauses: list = [LogEntry.server_id == server_id]
    if level:
        where_clauses.append(LogEntry.level == level.upper())
    if q:
        search = f"%{q.strip().lower()}%"
        if search != "%%":
            where_clauses.append(
                or_(
                    func.lower(LogEntry.message).like(search),
                    func.lower(LogEntry.raw_line).like(search),
                    func.lower(LogEntry.source_file).like(search),
                )
            )
    if from_dt:
        where_clauses.append(LogEntry.logged_at >= as_naive_utc(from_dt))
    if to_dt:
        where_clauses.append(LogEntry.logged_at <= as_naive_utc(to_dt))

    total = await db.scalar(
        select(func.count(LogEntry.id)).where(*where_clauses)
    ) or 0

    stmt = (
        select(LogEntry)
        .options(defer(LogEntry.raw_line))
        .where(*where_clauses)
        .order_by(LogEntry.logged_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(stmt)
    logs = result.scalars().all()

    return {
        "data": [LogEntryOut.model_validate(le).model_dump() for le in logs],
        "meta": {"total": total, "page": page, "per_page": per_page},
    }
