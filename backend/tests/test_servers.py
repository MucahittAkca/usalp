"""Sunucu endpoint testleri — liste, detay, metrik/servis/log sorguları."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.log_entry import LogEntry
from app.models.metric import Metric
from app.models.server import Server
from app.models.service_status import ServiceStatus


async def _seed_server(
    db: AsyncSession,
    name: str = "srv-01",
    *,
    environment: str = "production",
    group_name: str = "",
    tags: list[str] | None = None,
) -> Server:
    """Test veritabanına bir sunucu kaydı ekler."""
    server = Server(
        name=name,
        hostname=f"{name}.local",
        ip_address="10.0.0.1",
        api_key=f"key-{name}",
        environment=environment,
        group_name=group_name,
        tags=tags or [],
        status="active",
    )
    db.add(server)
    await db.commit()
    await db.refresh(server)
    return server


async def _seed_metrics(
    db: AsyncSession, server_id: int, count: int = 5, base_time: datetime | None = None,
) -> list[Metric]:
    """Belirtilen sayıda metrik kaydı oluşturur (30s aralıkla)."""
    base = base_time or datetime.now(UTC)
    metrics: list[Metric] = []
    for i in range(count):
        m = Metric(
            server_id=server_id,
            cpu_percent=20.0 + i,
            ram_percent=40.0 + i,
            disk_percent=50.0,
            network_in_bytes=1000 * (i + 1),
            network_out_bytes=500 * (i + 1),
            load_avg_1=0.5,
            load_avg_5=0.4,
            load_avg_15=0.3,
            recorded_at=base - timedelta(seconds=30 * i),
        )
        db.add(m)
        metrics.append(m)
    await db.commit()
    for m in metrics:
        await db.refresh(m)
    return metrics


async def _seed_services(
    db: AsyncSession, server_id: int,
    services: list[tuple[str, str]] | None = None,
) -> list[ServiceStatus]:
    """Servis durum kayıtları ekler."""
    services = services or [("nginx", "active"), ("postgresql", "active")]
    records: list[ServiceStatus] = []
    for name, status in services:
        s = ServiceStatus(server_id=server_id, service_name=name, status=status)
        db.add(s)
        records.append(s)
    await db.commit()
    return records


async def _seed_logs(
    db: AsyncSession, server_id: int, count: int = 5,
    level: str = "ERROR", base_time: datetime | None = None,
) -> list[LogEntry]:
    """Log entry kayıtları ekler."""
    base = base_time or datetime.now(UTC)
    logs: list[LogEntry] = []
    for i in range(count):
        le = LogEntry(
            server_id=server_id,
            source_file="/var/log/syslog",
            level=level,
            message=f"test message {i}",
            raw_line=f"raw line {i}",
            logged_at=base - timedelta(seconds=60 * i),
        )
        db.add(le)
        logs.append(le)
    await db.commit()
    return logs


# ---------------------------------------------------------------------------
# GET /servers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_servers_empty(client: AsyncClient, auth_headers: dict) -> None:
    """Sunucu yokken boş liste ve total=0 döner."""
    resp = await client.get("/api/v1/servers", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"] == []
    assert body["meta"]["total"] == 0


@pytest.mark.asyncio
async def test_list_servers_with_data(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict,
) -> None:
    """Sunucu varken doğru listeyi döner."""
    await _seed_server(db_session, "web-01")
    await _seed_server(db_session, "db-01")

    resp = await client.get("/api/v1/servers", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["meta"]["total"] == 2
    assert len(body["data"]) == 2
    names = {s["name"] for s in body["data"]}
    assert names == {"web-01", "db-01"}


@pytest.mark.asyncio
async def test_list_servers_pagination(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict,
) -> None:
    """Sayfalama doğru çalışır — page=1 per_page=2 ile 2 kayıt, page=2 ile kalanlar."""
    for i in range(5):
        await _seed_server(db_session, f"srv-{i:02d}")

    resp1 = await client.get("/api/v1/servers?page=1&per_page=2", headers=auth_headers)
    body1 = resp1.json()
    assert resp1.status_code == 200
    assert len(body1["data"]) == 2
    assert body1["meta"]["total"] == 5
    assert body1["meta"]["page"] == 1
    assert body1["meta"]["per_page"] == 2

    resp2 = await client.get("/api/v1/servers?page=3&per_page=2", headers=auth_headers)
    body2 = resp2.json()
    assert len(body2["data"]) == 1


@pytest.mark.asyncio
async def test_list_servers_filters_environment_group_and_tag(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict,
) -> None:
    """environment + group_name + tag filtreleri birlikte çalışır."""
    await _seed_server(
        db_session,
        "web-01",
        environment="production",
        group_name="edge",
        tags=["nginx", "public"],
    )
    await _seed_server(
        db_session,
        "worker-01",
        environment="production",
        group_name="workers",
        tags=["queue"],
    )
    await _seed_server(
        db_session,
        "web-staging",
        environment="staging",
        group_name="edge",
        tags=["nginx"],
    )

    resp = await client.get(
        "/api/v1/servers",
        params={"environment": "production", "group_name": "edge", "tag": "nginx"},
        headers=auth_headers,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["meta"]["total"] == 1
    assert body["data"][0]["name"] == "web-01"
    assert body["data"][0]["environment"] == "production"
    assert body["data"][0]["group_name"] == "edge"
    assert body["data"][0]["tags"] == ["nginx", "public"]


@pytest.mark.asyncio
async def test_list_servers_no_auth(client: AsyncClient) -> None:
    """Token olmadan 401 döner."""
    resp = await client.get("/api/v1/servers")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /servers/{server_id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_server_detail(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict,
) -> None:
    """Mevcut sunucu detayını döner, api_key sızdırmaz."""
    server = await _seed_server(db_session)

    resp = await client.get(f"/api/v1/servers/{server.id}", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["name"] == "srv-01"
    assert body["data"]["hostname"] == "srv-01.local"
    assert body["data"]["environment"] == "production"
    assert body["data"]["group_name"] == ""
    assert body["data"]["tags"] == []
    assert "api_key" not in body["data"]


@pytest.mark.asyncio
async def test_get_server_not_found(client: AsyncClient, auth_headers: dict) -> None:
    """Olmayan sunucu için 404 döner."""
    resp = await client.get("/api/v1/servers/9999", headers=auth_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /servers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_server_with_group_environment_and_tags(
    client: AsyncClient, auth_headers: dict,
) -> None:
    """Sunucu oluştururken grup, ortam ve etiket alanları kaydedilir."""
    resp = await client.post(
        "/api/v1/servers",
        json={
            "name": "Web 01",
            "hostname": "web-01.local",
            "ip_address": "10.0.0.1",
            "environment": "Production",
            "group_name": "Edge",
            "tags": ["Nginx", "Public", "nginx", ""],
        },
        headers=auth_headers,
    )

    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["environment"] == "production"
    assert data["group_name"] == "edge"
    assert data["tags"] == ["nginx", "public"]
    assert data["api_key"].startswith("usalp-")


# ---------------------------------------------------------------------------
# GET /servers/{server_id}/metrics — zaman filtresi + limit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_metrics_default_window(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict,
) -> None:
    """from_dt/to_dt verilmezse son 1 saatteki metrikler döner."""
    server = await _seed_server(db_session)
    now = datetime.now(UTC)
    await _seed_metrics(db_session, server.id, count=3, base_time=now)
    # 2 saat önce eklenen metrik — varsayılan pencere dışı
    old = Metric(
        server_id=server.id,
        cpu_percent=10.0, ram_percent=20.0, disk_percent=30.0,
        network_in_bytes=100, network_out_bytes=50,
        load_avg_1=0.1, load_avg_5=0.1, load_avg_15=0.1,
        recorded_at=now - timedelta(hours=2),
    )
    db_session.add(old)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/servers/{server.id}/metrics", headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["meta"]["total"] == 3
    assert len(body["data"]) == 3


@pytest.mark.asyncio
async def test_get_metrics_custom_time_range(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict,
) -> None:
    """from_dt/to_dt özel zaman aralığı sorgusu çalışır."""
    server = await _seed_server(db_session)
    base = datetime(2026, 3, 10, 12, 0, 0, tzinfo=UTC)

    await _seed_metrics(db_session, server.id, count=5, base_time=base)

    from_dt = (base - timedelta(seconds=90)).isoformat()
    to_dt = base.isoformat()

    resp = await client.get(
        f"/api/v1/servers/{server.id}/metrics",
        params={"from_dt": from_dt, "to_dt": to_dt},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["meta"]["total"] == 4
    assert len(body["data"]) == 4


@pytest.mark.asyncio
async def test_get_metrics_limit(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict,
) -> None:
    """limit parametresi döndürülen kayıt sayısını kısıtlar."""
    server = await _seed_server(db_session)
    now = datetime.now(UTC)
    await _seed_metrics(db_session, server.id, count=10, base_time=now)

    resp = await client.get(
        f"/api/v1/servers/{server.id}/metrics",
        params={"limit": 3},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) == 3
    assert body["meta"]["total"] == 10
    assert body["meta"]["limit"] == 3


@pytest.mark.asyncio
async def test_get_metrics_ordered_desc(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict,
) -> None:
    """Metrikler recorded_at DESC sıralı döner (en yeni ilk)."""
    server = await _seed_server(db_session)
    now = datetime.now(UTC)
    await _seed_metrics(db_session, server.id, count=3, base_time=now)

    resp = await client.get(
        f"/api/v1/servers/{server.id}/metrics", headers=auth_headers,
    )
    body = resp.json()
    timestamps = [d["recorded_at"] for d in body["data"]]
    assert timestamps == sorted(timestamps, reverse=True)


@pytest.mark.asyncio
async def test_get_metrics_no_raw_json(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict,
) -> None:
    """Liste endpoint'i raw_json alanını döndürmez."""
    server = await _seed_server(db_session)
    now = datetime.now(UTC)
    await _seed_metrics(db_session, server.id, count=1, base_time=now)

    resp = await client.get(
        f"/api/v1/servers/{server.id}/metrics", headers=auth_headers,
    )
    body = resp.json()
    assert len(body["data"]) == 1
    assert "raw_json" not in body["data"][0]


@pytest.mark.asyncio
async def test_get_metrics_empty(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict,
) -> None:
    """Metriği olmayan sunucu için boş liste döner."""
    server = await _seed_server(db_session)
    resp = await client.get(
        f"/api/v1/servers/{server.id}/metrics", headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"] == []


@pytest.mark.asyncio
async def test_get_metrics_server_not_found(
    client: AsyncClient, auth_headers: dict,
) -> None:
    """Olmayan sunucunun metrikleri sorgulanınca 404 döner."""
    resp = await client.get("/api/v1/servers/9999/metrics", headers=auth_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /servers/{server_id}/services
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_services_empty(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict,
) -> None:
    """Servisi olmayan sunucu için boş liste döner."""
    server = await _seed_server(db_session)
    resp = await client.get(
        f"/api/v1/servers/{server.id}/services", headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"] == []


@pytest.mark.asyncio
async def test_get_services_latest_snapshot(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict,
) -> None:
    """Aynı servisin birden fazla kaydı varsa en son snapshot döner."""
    server = await _seed_server(db_session)

    # nginx'in iki kaydı: önce active, sonra failed
    await _seed_services(db_session, server.id, [("nginx", "active")])
    await _seed_services(db_session, server.id, [("nginx", "failed")])
    await _seed_services(db_session, server.id, [("postgresql", "active")])

    resp = await client.get(
        f"/api/v1/servers/{server.id}/services", headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) == 2

    svc_map = {s["service_name"]: s["status"] for s in body["data"]}
    assert svc_map["nginx"] == "failed"
    assert svc_map["postgresql"] == "active"


@pytest.mark.asyncio
async def test_get_services_server_not_found(
    client: AsyncClient, auth_headers: dict,
) -> None:
    """Olmayan sunucunun servisleri sorgulanınca 404 döner."""
    resp = await client.get("/api/v1/servers/9999/services", headers=auth_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /servers/{server_id}/logs — level filtre + zaman filtre + pagination
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_logs_empty(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict,
) -> None:
    """Logu olmayan sunucu için boş liste döner."""
    server = await _seed_server(db_session)
    resp = await client.get(
        f"/api/v1/servers/{server.id}/logs", headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"] == []
    assert resp.json()["meta"]["total"] == 0


@pytest.mark.asyncio
async def test_get_logs_with_data(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict,
) -> None:
    """Log kayıtları doğru döner, raw_line alanı dahil edilmez."""
    server = await _seed_server(db_session)
    await _seed_logs(db_session, server.id, count=3, level="ERROR")

    resp = await client.get(
        f"/api/v1/servers/{server.id}/logs", headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["meta"]["total"] == 3
    assert len(body["data"]) == 3
    assert "raw_line" not in body["data"][0]
    assert body["data"][0]["level"] == "ERROR"


@pytest.mark.asyncio
async def test_get_logs_level_filter(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict,
) -> None:
    """Level filtresi sadece o seviyedeki logları döndürür."""
    server = await _seed_server(db_session)
    await _seed_logs(db_session, server.id, count=3, level="ERROR")
    await _seed_logs(db_session, server.id, count=2, level="WARNING")

    resp = await client.get(
        f"/api/v1/servers/{server.id}/logs",
        params={"level": "warning"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["meta"]["total"] == 2
    assert all(d["level"] == "WARNING" for d in body["data"])


@pytest.mark.asyncio
async def test_get_logs_search_query_backend_side(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict,
) -> None:
    """q parametresi mesaj, raw_line ve kaynak dosya üzerinde backend-side arar."""
    server = await _seed_server(db_session)
    base = datetime.now(UTC)
    logs = [
        LogEntry(
            server_id=server.id,
            source_file="/var/log/nginx/error.log",
            level="ERROR",
            message="upstream connection refused",
            raw_line="nginx raw line",
            logged_at=base,
        ),
        LogEntry(
            server_id=server.id,
            source_file="/var/log/app.log",
            level="ERROR",
            message="generic failure",
            raw_line="trace_id=abc123 hidden detail",
            logged_at=base - timedelta(seconds=1),
        ),
        LogEntry(
            server_id=server.id,
            source_file="/var/log/syslog",
            level="INFO",
            message="cron completed",
            raw_line="cron completed",
            logged_at=base - timedelta(seconds=2),
        ),
    ]
    db_session.add_all(logs)
    await db_session.commit()

    resp_message = await client.get(
        f"/api/v1/servers/{server.id}/logs",
        params={"q": "REFUSED"},
        headers=auth_headers,
    )
    assert resp_message.status_code == 200
    body_message = resp_message.json()
    assert body_message["meta"]["total"] == 1
    assert body_message["data"][0]["message"] == "upstream connection refused"

    resp_raw = await client.get(
        f"/api/v1/servers/{server.id}/logs",
        params={"q": "abc123"},
        headers=auth_headers,
    )
    assert resp_raw.json()["meta"]["total"] == 1
    assert resp_raw.json()["data"][0]["source_file"] == "/var/log/app.log"


@pytest.mark.asyncio
async def test_get_logs_time_filter(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict,
) -> None:
    """from_dt/to_dt ile zaman aralığı filtresi çalışır."""
    server = await _seed_server(db_session)
    base = datetime(2026, 3, 10, 12, 0, 0, tzinfo=UTC)
    await _seed_logs(db_session, server.id, count=5, base_time=base)

    from_dt = (base - timedelta(minutes=2, seconds=30)).isoformat()
    to_dt = base.isoformat()

    resp = await client.get(
        f"/api/v1/servers/{server.id}/logs",
        params={"from_dt": from_dt, "to_dt": to_dt},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["meta"]["total"] == 3


@pytest.mark.asyncio
async def test_get_logs_pagination(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict,
) -> None:
    """Sayfalama doğru çalışır."""
    server = await _seed_server(db_session)
    await _seed_logs(db_session, server.id, count=7)

    resp1 = await client.get(
        f"/api/v1/servers/{server.id}/logs",
        params={"page": 1, "per_page": 3},
        headers=auth_headers,
    )
    body1 = resp1.json()
    assert len(body1["data"]) == 3
    assert body1["meta"]["total"] == 7
    assert body1["meta"]["page"] == 1

    resp2 = await client.get(
        f"/api/v1/servers/{server.id}/logs",
        params={"page": 3, "per_page": 3},
        headers=auth_headers,
    )
    body2 = resp2.json()
    assert len(body2["data"]) == 1


@pytest.mark.asyncio
async def test_get_logs_ordered_desc(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict,
) -> None:
    """Loglar logged_at DESC sıralı döner (en yeni ilk)."""
    server = await _seed_server(db_session)
    await _seed_logs(db_session, server.id, count=4)

    resp = await client.get(
        f"/api/v1/servers/{server.id}/logs", headers=auth_headers,
    )
    body = resp.json()
    timestamps = [d["logged_at"] for d in body["data"]]
    assert timestamps == sorted(timestamps, reverse=True)


@pytest.mark.asyncio
async def test_get_logs_server_not_found(
    client: AsyncClient, auth_headers: dict,
) -> None:
    """Olmayan sunucunun logları sorgulanınca 404 döner."""
    resp = await client.get("/api/v1/servers/9999/logs", headers=auth_headers)
    assert resp.status_code == 404
