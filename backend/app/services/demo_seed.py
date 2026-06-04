"""Demo modu için deterministik örnek veri üretimi."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_api_key
from app.models.ai_analysis import AIAnalysis
from app.models.alert import Alert
from app.models.log_entry import LogEntry
from app.models.metric import Metric
from app.models.server import Server
from app.models.service_status import ServiceStatus

DEMO_API_KEY_PREFIX = "usalp-demo-"
DEMO_HOST_SUFFIX = ".usalp.demo"


def _initial_demo_reference() -> datetime:
    """İlk demo seed için stabil ve grafiklerde güncel görünen zaman ankrajı."""
    now = datetime.now(UTC).replace(second=0, microsecond=0)
    rounded_minute = (now.minute // 15) * 15
    return now.replace(minute=rounded_minute)


def _latest_metric_reference_offset() -> timedelta:
    """En güncel demo metriğinden seed ankrajına geri dönecek offset'i hesaplar."""
    deltas = [
        spec.last_seen_delta
        for spec in _demo_specs()
        if spec.last_seen_delta is not None
    ]
    return min(deltas) if deltas else timedelta()


async def _demo_reference_from_existing_data(db: AsyncSession) -> datetime | None:
    """Restart/reset sırasında mevcut demo zaman ankrajını korur."""
    latest_metric_at = await db.scalar(
        select(func.max(Metric.recorded_at))
        .join(Server, Metric.server_id == Server.id)
        .where(Server.hostname.like(f"%{DEMO_HOST_SUFFIX}"))
    )
    if latest_metric_at is None:
        return None
    if latest_metric_at.tzinfo is None:
        latest_metric_at = latest_metric_at.replace(tzinfo=UTC)
    else:
        latest_metric_at = latest_metric_at.astimezone(UTC)
    return latest_metric_at + _latest_metric_reference_offset()


@dataclass(frozen=True)
class DemoAlertSpec:
    """Demo alert tanımı."""

    type: str
    dedupe_key: str
    severity: str
    message: str
    created_delta: timedelta
    resolved_delta: timedelta | None = None


@dataclass(frozen=True)
class DemoAnalysisSpec:
    """LLM key olmadan demo ekranını dolduran örnek analiz tanımı."""

    alert_dedupe_key: str
    category: str
    severity: str
    summary: str
    causes: tuple[str, ...]
    evidence_lines: tuple[str, ...]
    commands: tuple[dict[str, str], ...]
    confidence: float
    created_delta: timedelta


@dataclass(frozen=True)
class DemoServerSpec:
    """Demo sunucu ve davranış profili."""

    key: str
    name: str
    hostname: str
    ip_address: str
    environment: str
    group_name: str
    tags: tuple[str, ...]
    status: str
    last_seen_delta: timedelta | None
    cpu_base: float
    ram_base: float
    disk_base: float
    services: tuple[tuple[str, str], ...]
    alerts: tuple[DemoAlertSpec, ...] = ()
    analyses: tuple[DemoAnalysisSpec, ...] = ()


@dataclass(frozen=True)
class DemoSeedResult:
    """Seed işlemi özeti."""

    servers: int = 0
    metrics: int = 0
    logs: int = 0
    services: int = 0
    alerts: int = 0
    analyses: int = 0
    skipped: bool = False


def _clamp_percent(value: float) -> float:
    """Yüzde değerini 0-100 aralığına sabitler."""
    return round(max(0.0, min(100.0, value)), 2)


def _demo_specs() -> tuple[DemoServerSpec, ...]:
    """Dashboard'daki tüm yeni özellikleri gösterecek demo profilleri."""
    return (
        DemoServerSpec(
            key="prod-web-01",
            name="prod-web-01",
            hostname="prod-web-01.usalp.demo",
            ip_address="10.20.0.11",
            environment="production",
            group_name="edge",
            tags=("nginx", "public", "critical"),
            status="warning",
            last_seen_delta=timedelta(seconds=35),
            cpu_base=52.0,
            ram_base=68.0,
            disk_base=71.0,
            services=(("nginx", "failed"), ("ssh", "active"), ("node-exporter", "active")),
            alerts=(
                DemoAlertSpec(
                    type="cpu_threshold",
                    dedupe_key="cpu_threshold",
                    severity="critical",
                    message="CPU kullanımı kritik: %94.2",
                    created_delta=timedelta(minutes=21),
                ),
                DemoAlertSpec(
                    type="service_failed",
                    dedupe_key="service_failed:nginx",
                    severity="critical",
                    message="Servis durumu: nginx failed",
                    created_delta=timedelta(minutes=18),
                ),
            ),
            analyses=(
                DemoAnalysisSpec(
                    alert_dedupe_key="service_failed:nginx",
                    category="dependency_failure",
                    severity="critical",
                    summary=(
                        "[DEMO] prod-web-01 üzerinde nginx servisi failed durumda ve "
                        "upstream bağlantı hataları aynı zaman aralığında yoğunlaşıyor."
                    ),
                    causes=(
                        "Nginx'in bağlanmaya çalıştığı checkout-api socket'i veya upstream servisi kapalı olabilir.",
                        "Yük artışı worker bağlantı limitlerine çarparak nginx hatalarını artırmış olabilir.",
                    ),
                    evidence_lines=(
                        "[SERVICE] nginx failed",
                        "[ERROR] /var/log/nginx/error.log: upstream connect() failed (111: Connection refused)",
                        "[WARNING] /var/log/nginx/error.log: worker_connections are not enough for current traffic",
                    ),
                    commands=(
                        {
                            "command": "systemctl status nginx --no-pager",
                            "description": "Nginx servis durumunu ve son hata özetini kontrol et",
                            "risk_level": "low",
                        },
                        {
                            "command": "journalctl -u nginx --no-pager -n 80",
                            "description": "Nginx servis loglarında çökme nedenini incele",
                            "risk_level": "low",
                        },
                        {
                            "command": "ss -ltnp | grep -E '(:80|:443|api.sock)'",
                            "description": "Beklenen port veya socket dinleniyor mu kontrol et",
                            "risk_level": "low",
                        },
                    ),
                    confidence=0.86,
                    created_delta=timedelta(minutes=14),
                ),
            ),
        ),
        DemoServerSpec(
            key="prod-db-01",
            name="prod-db-01",
            hostname="prod-db-01.usalp.demo",
            ip_address="10.20.0.21",
            environment="production",
            group_name="database",
            tags=("postgres", "storage", "critical"),
            status="warning",
            last_seen_delta=timedelta(seconds=50),
            cpu_base=38.0,
            ram_base=74.0,
            disk_base=91.5,
            services=(("postgresql", "active"), ("ssh", "active"), ("backup.timer", "failed")),
            alerts=(
                DemoAlertSpec(
                    type="disk_threshold",
                    dedupe_key="disk_threshold",
                    severity="critical",
                    message="Disk kullanımı kritik: %96.8",
                    created_delta=timedelta(hours=1, minutes=4),
                ),
            ),
            analyses=(
                DemoAnalysisSpec(
                    alert_dedupe_key="disk_threshold",
                    category="disk_issue",
                    severity="high",
                    summary=(
                        "[DEMO] prod-db-01 üzerinde disk doluluğu kritik eşikte ve "
                        "PostgreSQL dosya genişletme hatası raporluyor."
                    ),
                    causes=(
                        "PostgreSQL WAL, geçici dosya veya tablo büyümesi diski doldurmuş olabilir.",
                        "backup.timer başarısız olduğu için eski yedek veya arşiv dosyaları temizlenmemiş olabilir.",
                    ),
                    evidence_lines=(
                        "[METRIC] Disk kullanımı kritik: %96.8",
                        "[ERROR] /var/log/postgresql/postgresql-16-main.log: could not extend file: No space left on device",
                        "[SERVICE] backup.timer failed",
                    ),
                    commands=(
                        {
                            "command": "df -h /var/lib/postgresql",
                            "description": "PostgreSQL veri dizininin disk doluluğunu kontrol et",
                            "risk_level": "low",
                        },
                        {
                            "command": "du -xh /var/lib/postgresql | sort -h | tail -20",
                            "description": "En fazla yer kaplayan PostgreSQL alt dizinlerini listele",
                            "risk_level": "low",
                        },
                        {
                            "command": "systemctl status backup.timer --no-pager",
                            "description": "Yedekleme zamanlayıcısının neden başarısız olduğunu incele",
                            "risk_level": "low",
                        },
                    ),
                    confidence=0.84,
                    created_delta=timedelta(minutes=42),
                ),
            ),
        ),
        DemoServerSpec(
            key="staging-worker-01",
            name="staging-worker-01",
            hostname="staging-worker-01.usalp.demo",
            ip_address="10.30.0.31",
            environment="staging",
            group_name="workers",
            tags=("queue", "python", "staging"),
            status="online",
            last_seen_delta=timedelta(seconds=75),
            cpu_base=44.0,
            ram_base=58.0,
            disk_base=42.0,
            services=(("usalp-worker", "active"), ("redis-client", "active"), ("ssh", "active")),
            alerts=(
                DemoAlertSpec(
                    type="critical_log_burst",
                    dedupe_key="critical_log_burst",
                    severity="warning",
                    message="6 kritik/hata logu tespit edildi",
                    created_delta=timedelta(hours=5),
                    resolved_delta=timedelta(hours=4, minutes=20),
                ),
            ),
        ),
        DemoServerSpec(
            key="dev-cache-01",
            name="dev-cache-01",
            hostname="dev-cache-01.usalp.demo",
            ip_address="10.40.0.41",
            environment="development",
            group_name="cache",
            tags=("redis", "dev"),
            status="offline",
            last_seen_delta=timedelta(hours=3, minutes=12),
            cpu_base=18.0,
            ram_base=35.0,
            disk_base=28.0,
            services=(("redis-server", "failed"), ("ssh", "active")),
        ),
    )


async def _reset_existing_demo_data(
    db: AsyncSession,
    expected_hostnames: set[str],
) -> dict[str, Server]:
    """Önceki demo child verisini temizler, mevcut demo server ID'lerini korur."""
    result = await db.execute(
        select(Server).where(Server.hostname.like(f"%{DEMO_HOST_SUFFIX}"))
    )
    existing_servers = {
        server.hostname: server
        for server in result.scalars().all()
    }
    server_ids = [server.id for server in existing_servers.values()]
    if not server_ids:
        return {}

    for model in (AIAnalysis, Alert, LogEntry, ServiceStatus, Metric):
        await db.execute(delete(model).where(model.server_id.in_(server_ids)))

    stale_server_ids = [
        server.id
        for hostname, server in existing_servers.items()
        if hostname not in expected_hostnames
    ]
    if stale_server_ids:
        await db.execute(delete(Server).where(Server.id.in_(stale_server_ids)))
        existing_servers = {
            hostname: server
            for hostname, server in existing_servers.items()
            if hostname in expected_hostnames
        }

    await db.flush()
    return existing_servers


def _metric_timestamps(reference: datetime) -> list[datetime]:
    """Son 24 saat yoğun, önceki günler seyrek olacak şekilde zaman noktaları üretir."""
    older = [reference - timedelta(hours=6 * offset) for offset in range(28, 4, -1)]
    recent = [reference - timedelta(minutes=15 * offset) for offset in range(96, -1, -1)]
    return older + recent


def _metric_values(spec: DemoServerSpec, index: int, total: int) -> tuple[float, float, float]:
    """Profil bazlı metrik eğrisi üretir."""
    position = index / max(total - 1, 1)
    daily_wave = math.sin(index / 5.0)
    cpu = spec.cpu_base + daily_wave * 7.5
    ram = spec.ram_base + math.sin(index / 8.0) * 4.0
    disk = spec.disk_base + position * 3.0

    if spec.key == "prod-web-01" and position > 0.82:
        cpu += (position - 0.82) * 205
        ram += (position - 0.82) * 45
    elif spec.key == "prod-db-01":
        disk += position * 2.5
        ram += 3.0
    elif spec.key == "staging-worker-01" and 0.55 < position < 0.72:
        cpu += 17.0
        ram += 12.0

    return _clamp_percent(cpu), _clamp_percent(ram), _clamp_percent(disk)


def _raw_metric_payload(
    spec: DemoServerSpec,
    recorded_at: datetime,
    cpu: float,
    ram: float,
    disk: float,
) -> dict[str, Any]:
    """Metrik detaylarında görülebilecek sade payload üretir."""
    total_memory = 16 * 1024 * 1024 * 1024
    used_memory = int(total_memory * ram / 100)
    return {
        "server_id": spec.hostname,
        "collected_at": recorded_at.isoformat(),
        "cpu": {
            "percent": cpu,
            "per_core": [round(max(0.0, cpu - 4.0), 2), cpu, round(min(100.0, cpu + 3.0), 2)],
            "load_avg_1": round(cpu / 24.0, 2),
            "load_avg_5": round(cpu / 28.0, 2),
            "load_avg_15": round(cpu / 32.0, 2),
        },
        "memory": {
            "total_bytes": total_memory,
            "used_bytes": used_memory,
            "available_bytes": total_memory - used_memory,
            "percent": ram,
        },
        "disks": [
            {
                "path": "/",
                "total_bytes": 120 * 1024 * 1024 * 1024,
                "used_bytes": int(120 * 1024 * 1024 * 1024 * disk / 100),
                "free_bytes": int(120 * 1024 * 1024 * 1024 * (100 - disk) / 100),
                "percent": disk,
            }
        ],
        "networks": [
            {
                "interface": "eth0",
                "bytes_recv_per_sec": int(90_000 + cpu * 2800),
                "bytes_sent_per_sec": int(55_000 + cpu * 1700),
            }
        ],
    }


def _build_metrics(spec: DemoServerSpec, server_id: int, reference: datetime) -> list[Metric]:
    """Bir demo sunucusu için zaman serisi üretir."""
    timestamps = _metric_timestamps(reference)
    metrics: list[Metric] = []
    for index, recorded_at in enumerate(timestamps):
        cpu, ram, disk = _metric_values(spec, index, len(timestamps))
        metrics.append(
            Metric(
                server_id=server_id,
                cpu_percent=cpu,
                ram_percent=ram,
                disk_percent=disk,
                network_in_bytes=int(90_000 + cpu * 2800),
                network_out_bytes=int(55_000 + cpu * 1700),
                load_avg_1=round(cpu / 24.0, 2),
                load_avg_5=round(cpu / 28.0, 2),
                load_avg_15=round(cpu / 32.0, 2),
                raw_json=_raw_metric_payload(spec, recorded_at, cpu, ram, disk),
                recorded_at=recorded_at,
            )
        )
    return metrics


def _log_messages(spec: DemoServerSpec) -> tuple[tuple[str, str, str], ...]:
    """Profil bazlı demo log satırları."""
    if spec.key == "prod-web-01":
        return (
            ("ERROR", "/var/log/nginx/error.log", "upstream connect() failed (111: Connection refused) while connecting to upstream"),
            ("ERROR", "/var/log/nginx/error.log", "connect() to unix:/run/api.sock failed: REFUSED checkout-api"),
            ("WARNING", "/var/log/nginx/error.log", "worker_connections are not enough for current traffic"),
            ("INFO", "/var/log/nginx/access.log", "GET /checkout 200 183ms"),
            ("ERROR", "/var/log/syslog", "nginx.service: Main process exited, code=exited, status=1/FAILURE"),
            ("INFO", "/var/log/syslog", "Started node exporter"),
        )
    if spec.key == "prod-db-01":
        return (
            ("ERROR", "/var/log/postgresql/postgresql-16-main.log", "could not extend file: No space left on device"),
            ("WARNING", "/var/log/postgresql/postgresql-16-main.log", "remaining connection slots are reserved for superuser connections"),
            ("ERROR", "/var/log/syslog", "backup.timer failed with result exit-code"),
            ("INFO", "/var/log/postgresql/postgresql-16-main.log", "checkpoint starting: time"),
            ("WARNING", "/var/log/syslog", "filesystem /var/lib/postgresql is 96 percent full"),
        )
    if spec.key == "staging-worker-01":
        return (
            ("WARNING", "/var/log/usalp-worker.log", "queue backlog exceeded 1500 jobs"),
            ("ERROR", "/var/log/usalp-worker.log", "timeout contacting redis after 3 retries"),
            ("INFO", "/var/log/usalp-worker.log", "processed deployment-preview job abc123"),
            ("INFO", "/var/log/syslog", "usalp-worker.service is active"),
            ("WARNING", "/var/log/usalp-worker.log", "job retry rate returned to normal"),
        )
    return (
        ("ERROR", "/var/log/redis/redis-server.log", "RDB snapshot failed: Permission denied"),
        ("WARNING", "/var/log/redis/redis-server.log", "redis-server stopped accepting connections"),
        ("INFO", "/var/log/syslog", "developer instance scheduled maintenance started"),
    )


def _build_logs(spec: DemoServerSpec, server_id: int, reference: datetime) -> list[LogEntry]:
    """Bir demo sunucusu için log kayıtları üretir."""
    logs: list[LogEntry] = []
    messages = _log_messages(spec)
    for index in range(18):
        level, source_file, message = messages[index % len(messages)]
        logged_at = reference - timedelta(minutes=7 * index)
        logs.append(
            LogEntry(
                server_id=server_id,
                source_file=source_file,
                level=level,
                message=message,
                raw_line=f"{logged_at.isoformat()} {spec.hostname} {level} {message}",
                logged_at=logged_at,
            )
        )
    return logs


def _build_services(
    spec: DemoServerSpec,
    server_id: int,
    reference: datetime,
) -> list[ServiceStatus]:
    """Bir demo sunucusu için servis snapshot'ları üretir."""
    return [
        ServiceStatus(
            server_id=server_id,
            service_name=service_name,
            status=status,
            checked_at=reference - timedelta(seconds=index * 20),
        )
        for index, (service_name, status) in enumerate(spec.services)
    ]


def _build_alerts(
    spec: DemoServerSpec,
    server_id: int,
    now: datetime,
) -> list[Alert]:
    """Bir demo sunucusu için alert kayıtları üretir."""
    return [
        Alert(
            server_id=server_id,
            type=alert.type,
            dedupe_key=alert.dedupe_key,
            severity=alert.severity,
            message=alert.message,
            created_at=now - alert.created_delta,
            resolved_at=now - alert.resolved_delta if alert.resolved_delta else None,
        )
        for alert in spec.alerts
    ]


def _build_analysis(
    analysis: DemoAnalysisSpec,
    server_id: int,
    alert_id: int | None,
    now: datetime,
) -> AIAnalysis:
    """Bir demo AI analiz kaydı üretir."""
    return AIAnalysis(
        alert_id=alert_id,
        server_id=server_id,
        category=analysis.category,
        severity=analysis.severity,
        summary=analysis.summary,
        causes=json.dumps(list(analysis.causes), ensure_ascii=False),
        evidence_lines=json.dumps(list(analysis.evidence_lines), ensure_ascii=False),
        commands=json.dumps(list(analysis.commands), ensure_ascii=False),
        confidence=analysis.confidence,
        created_at=now - analysis.created_delta,
    )


async def seed_demo_data(db: AsyncSession, *, reset: bool = True) -> DemoSeedResult:
    """Demo verisini oluşturur.

    reset=True önceki demo verisini silip tekrar üretir. Kullanıcının manuel
    oluşturduğu kayıtlar korunur çünkü yalnızca demo hostname suffix'i hedeflenir.
    """
    existing_demo = await db.scalar(
        select(Server.id).where(Server.hostname.like(f"%{DEMO_HOST_SUFFIX}")).limit(1)
    )
    if existing_demo and not reset:
        return DemoSeedResult(skipped=True)

    reference_at = await _demo_reference_from_existing_data(db)

    now_aware = reference_at or _initial_demo_reference()
    # Eski şemada yalnızca servers.last_seen timezone-aware; metrik/log/alert
    # tarih kolonları PostgreSQL'de TIMESTAMP WITHOUT TIME ZONE.
    now = now_aware.replace(tzinfo=None)
    counts = DemoSeedResult()
    server_specs = _demo_specs()
    existing_servers: dict[str, Server] = {}

    if reset:
        expected_hostnames = {spec.hostname for spec in server_specs}
        existing_servers = await _reset_existing_demo_data(db, expected_hostnames)

    metrics_count = 0
    logs_count = 0
    services_count = 0
    alerts_count = 0
    analyses_count = 0

    for spec in server_specs:
        last_seen = now_aware - spec.last_seen_delta if spec.last_seen_delta else None
        reference = now - spec.last_seen_delta if spec.last_seen_delta else now
        server = existing_servers.get(spec.hostname)
        if server is None:
            server = Server(hostname=spec.hostname)
            db.add(server)

        server.name = spec.name
        server.hostname = spec.hostname
        server.ip_address = spec.ip_address
        server.api_key = hash_api_key(f"{DEMO_API_KEY_PREFIX}{spec.key}")
        server.environment = spec.environment
        server.group_name = spec.group_name
        server.tags = list(spec.tags)
        server.status = spec.status
        server.last_seen = last_seen
        server.api_key_revoked_at = None
        await db.flush()

        metric_rows = _build_metrics(spec, server.id, reference)
        service_rows = _build_services(spec, server.id, reference)
        log_rows = _build_logs(spec, server.id, reference)
        alert_rows = _build_alerts(spec, server.id, now)

        db.add_all(metric_rows)
        db.add_all(service_rows)
        db.add_all(log_rows)
        db.add_all(alert_rows)
        await db.flush()

        alerts_by_dedupe = {alert.dedupe_key: alert for alert in alert_rows}
        for analysis_spec in spec.analyses:
            alert = alerts_by_dedupe.get(analysis_spec.alert_dedupe_key)
            db.add(_build_analysis(analysis_spec, server.id, alert.id if alert else None, now))
            analyses_count += 1

        metrics_count += len(metric_rows)
        logs_count += len(log_rows)
        services_count += len(service_rows)
        alerts_count += len(alert_rows)

    await db.flush()
    counts = DemoSeedResult(
        servers=len(server_specs),
        metrics=metrics_count,
        logs=logs_count,
        services=services_count,
        alerts=alerts_count,
        analyses=analyses_count,
    )
    return counts
