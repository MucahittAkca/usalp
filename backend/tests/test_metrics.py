"""POST /api/v1/metrics endpoint + metric_service unit + alert engine testleri."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.log_entry import LogEntry
from app.models.metric import Metric
from app.models.server import Server
from app.models.service_status import ServiceStatus
from app.schemas.metric import LogData, MetricPayload, ServiceData
from app.services import alert_engine, metric_service

SAMPLE_PAYLOAD = {
    "server_id": "web-01",
    "collected_at": "2026-03-11T12:00:00Z",
    "cpu": {
        "percent": 45.2,
        "per_core": [40.0, 50.0],
        "load_avg_1": 1.2,
        "load_avg_5": 1.0,
        "load_avg_15": 0.8,
    },
    "memory": {
        "total_bytes": 8_000_000_000,
        "used_bytes": 4_000_000_000,
        "available_bytes": 4_000_000_000,
        "cached_bytes": 1_000_000_000,
        "percent": 50.0,
        "swap_total_bytes": 2_000_000_000,
        "swap_used_bytes": 0,
    },
    "disks": [
        {
            "path": "/",
            "total_bytes": 100_000_000_000,
            "used_bytes": 60_000_000_000,
            "free_bytes": 40_000_000_000,
            "percent": 60.0,
            "read_bytes_per_sec": 1024.0,
            "write_bytes_per_sec": 512.0,
        }
    ],
    "networks": [
        {
            "interface": "eth0",
            "bytes_sent_per_sec": 5000.0,
            "bytes_recv_per_sec": 15000.0,
            "packets_sent_per_sec": 50.0,
            "packets_recv_per_sec": 100.0,
            "errors_in": 0,
            "errors_out": 0,
        }
    ],
    "top_processes": [
        {
            "pid": 1234,
            "name": "python",
            "cpu_percent": 12.5,
            "memory_percent": 3.2,
            "status": "running",
        }
    ],
    "services": [
        {"name": "nginx", "status": "active", "sub_state": "running"},
    ],
    "log_entries": [
        {
            "source_file": "/var/log/syslog",
            "level": "ERROR",
            "message": "disk I/O error",
            "raw_line": "Mar 11 12:00:00 host kernel: disk I/O error",
            "logged_at": "2026-03-11T12:00:00Z",
        }
    ],
}


async def _seed_server(db: AsyncSession) -> Server:
    """Test veritabanına bir sunucu kaydı ekler."""
    server = Server(
        name="web-01",
        hostname="web-01.local",
        ip_address="10.0.0.1",
        api_key="test-api-key-123",
        status="inactive",
    )
    db.add(server)
    await db.commit()
    await db.refresh(server)
    return server


def _make_payload(**overrides: object) -> dict:
    """SAMPLE_PAYLOAD'un kopyasını override'larla döndürür."""
    data = deepcopy(SAMPLE_PAYLOAD)
    for key, val in overrides.items():
        keys = key.split("__")
        target = data
        for k in keys[:-1]:
            target = target[k]
        target[keys[-1]] = val
    return data


# ===================================================================
# 1. POST /api/v1/metrics — Endpoint testleri
# ===================================================================


@pytest.mark.asyncio
async def test_post_metrics_accepted(client: AsyncClient, db_session: AsyncSession) -> None:
    """Geçerli payload ve Bearer token ile 202 Accepted döner."""
    await _seed_server(db_session)
    resp = await client.post(
        "/api/v1/metrics",
        json=SAMPLE_PAYLOAD,
        headers={"Authorization": "Bearer test-api-key-123"},
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["data"]["status"] == "accepted"
    assert "timestamp" in body["meta"]


@pytest.mark.asyncio
async def test_post_metrics_response_format(client: AsyncClient, db_session: AsyncSession) -> None:
    """Yanıt standart {data, meta} formatına uygun."""
    await _seed_server(db_session)
    resp = await client.post(
        "/api/v1/metrics",
        json=SAMPLE_PAYLOAD,
        headers={"Authorization": "Bearer test-api-key-123"},
    )
    body = resp.json()
    assert "data" in body
    assert "meta" in body
    assert isinstance(body["meta"]["timestamp"], str)


@pytest.mark.asyncio
async def test_post_metrics_invalid_api_key(client: AsyncClient) -> None:
    """Geçersiz API key ile 401 Unauthorized döner."""
    resp = await client.post(
        "/api/v1/metrics",
        json=SAMPLE_PAYLOAD,
        headers={"Authorization": "Bearer wrong-key"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_post_metrics_missing_auth_header(client: AsyncClient) -> None:
    """Authorization header eksikken 401 döner."""
    resp = await client.post("/api/v1/metrics", json=SAMPLE_PAYLOAD)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_post_metrics_invalid_payload(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    """Eksik alan ile 422 Validation Error döner."""
    await _seed_server(db_session)
    resp = await client.post(
        "/api/v1/metrics",
        json={"server_id": "x"},
        headers={"Authorization": "Bearer test-api-key-123"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_post_metrics_extra_field_rejected(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    """Bilinmeyen field gönderildiğinde 422 döner (extra='forbid')."""
    await _seed_server(db_session)
    payload = deepcopy(SAMPLE_PAYLOAD)
    payload["unknown_field"] = "test"
    resp = await client.post(
        "/api/v1/metrics",
        json=payload,
        headers={"Authorization": "Bearer test-api-key-123"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_post_metrics_empty_body(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    """Boş body ile 422 döner."""
    await _seed_server(db_session)
    resp = await client.post(
        "/api/v1/metrics",
        json={},
        headers={"Authorization": "Bearer test-api-key-123"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_post_metrics_empty_services_and_logs(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    """Boş services ve log_entries listesiyle 202 döner (hata vermez)."""
    await _seed_server(db_session)
    payload = _make_payload()
    payload["services"] = []
    payload["log_entries"] = []
    resp = await client.post(
        "/api/v1/metrics",
        json=payload,
        headers={"Authorization": "Bearer test-api-key-123"},
    )
    assert resp.status_code == 202


@pytest.mark.asyncio
async def test_post_metrics_sequential_writes(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    """Ardışık iki metrik gönderimi iki ayrı kayıt oluşturur."""
    await _seed_server(db_session)
    headers = {"Authorization": "Bearer test-api-key-123"}

    p1 = _make_payload(cpu__percent=30.0)
    p1["collected_at"] = "2026-03-11T12:00:00Z"
    await client.post("/api/v1/metrics", json=p1, headers=headers)

    p2 = _make_payload(cpu__percent=60.0)
    p2["collected_at"] = "2026-03-11T12:01:00Z"
    await client.post("/api/v1/metrics", json=p2, headers=headers)

    result = await db_session.execute(select(Metric))
    metrics = result.scalars().all()
    assert len(metrics) == 2
    cpus = sorted(m.cpu_percent for m in metrics)
    assert cpus == pytest.approx([30.0, 60.0])


# ===================================================================
# 2. DB yazma doğrulama testleri
# ===================================================================


@pytest.mark.asyncio
async def test_metric_saved_to_db(client: AsyncClient, db_session: AsyncSession) -> None:
    """POST sonrası metrik tablosuna doğru değerler yazılır."""
    await _seed_server(db_session)
    await client.post(
        "/api/v1/metrics",
        json=SAMPLE_PAYLOAD,
        headers={"Authorization": "Bearer test-api-key-123"},
    )

    result = await db_session.execute(select(Metric))
    metrics = result.scalars().all()
    assert len(metrics) == 1

    m = metrics[0]
    assert m.cpu_percent == pytest.approx(45.2)
    assert m.ram_percent == pytest.approx(50.0)
    assert m.disk_percent == pytest.approx(60.0)
    assert m.network_in_bytes == 15000
    assert m.network_out_bytes == 5000
    assert m.load_avg_1 == pytest.approx(1.2)
    assert m.raw_json is not None


@pytest.mark.asyncio
async def test_services_saved_to_db(client: AsyncClient, db_session: AsyncSession) -> None:
    """POST sonrası servis durumları service_statuses tablosuna yazılır."""
    await _seed_server(db_session)
    await client.post(
        "/api/v1/metrics",
        json=SAMPLE_PAYLOAD,
        headers={"Authorization": "Bearer test-api-key-123"},
    )

    result = await db_session.execute(select(ServiceStatus))
    services = result.scalars().all()
    assert len(services) == 1
    assert services[0].service_name == "nginx"
    assert services[0].status == "active"


@pytest.mark.asyncio
async def test_logs_saved_to_db(client: AsyncClient, db_session: AsyncSession) -> None:
    """POST sonrası log entry'leri log_entries tablosuna yazılır."""
    await _seed_server(db_session)
    await client.post(
        "/api/v1/metrics",
        json=SAMPLE_PAYLOAD,
        headers={"Authorization": "Bearer test-api-key-123"},
    )

    result = await db_session.execute(select(LogEntry))
    logs = result.scalars().all()
    assert len(logs) == 1
    assert logs[0].level == "ERROR"
    assert logs[0].source_file == "/var/log/syslog"


@pytest.mark.asyncio
async def test_server_status_updated_to_active(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    """Metrik alındığında sunucu status='active' olarak güncellenir."""
    server = await _seed_server(db_session)
    assert server.status == "inactive"

    await client.post(
        "/api/v1/metrics",
        json=SAMPLE_PAYLOAD,
        headers={"Authorization": "Bearer test-api-key-123"},
    )

    await db_session.refresh(server)
    assert server.status == "active"


# ===================================================================
# 3. metric_service unit testleri
# ===================================================================


@pytest.mark.asyncio
async def test_save_metric_multiple_disks_takes_max(db_session: AsyncSession) -> None:
    """Birden fazla disk bölümü varken en yüksek yüzde alınır."""
    server = await _seed_server(db_session)
    data = _make_payload()
    data["disks"] = [
        {**data["disks"][0], "path": "/", "percent": 40.0},
        {**data["disks"][0], "path": "/home", "percent": 85.0},
        {**data["disks"][0], "path": "/var", "percent": 55.0},
    ]
    payload = MetricPayload(**data)

    metric = await metric_service.save_metric(db_session, server.id, payload)
    assert metric.disk_percent == pytest.approx(85.0)


@pytest.mark.asyncio
async def test_save_metric_multiple_networks_sums_bytes(db_session: AsyncSession) -> None:
    """Birden fazla ağ arayüzü varken bytes toplamı alınır."""
    server = await _seed_server(db_session)
    data = _make_payload()
    data["networks"] = [
        {**data["networks"][0], "interface": "eth0", "bytes_recv_per_sec": 1000.0, "bytes_sent_per_sec": 500.0},
        {**data["networks"][0], "interface": "eth1", "bytes_recv_per_sec": 2000.0, "bytes_sent_per_sec": 1500.0},
    ]
    payload = MetricPayload(**data)

    metric = await metric_service.save_metric(db_session, server.id, payload)
    assert metric.network_in_bytes == 3000
    assert metric.network_out_bytes == 2000


@pytest.mark.asyncio
async def test_save_metric_no_disks_defaults_zero(db_session: AsyncSession) -> None:
    """Disk listesi boşsa disk_percent 0.0 olur."""
    server = await _seed_server(db_session)
    data = _make_payload()
    data["disks"] = []
    payload = MetricPayload(**data)

    metric = await metric_service.save_metric(db_session, server.id, payload)
    assert metric.disk_percent == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_save_metric_no_networks_defaults_zero(db_session: AsyncSession) -> None:
    """Network listesi boşsa bytes 0 olur."""
    server = await _seed_server(db_session)
    data = _make_payload()
    data["networks"] = []
    payload = MetricPayload(**data)

    metric = await metric_service.save_metric(db_session, server.id, payload)
    assert metric.network_in_bytes == 0
    assert metric.network_out_bytes == 0


@pytest.mark.asyncio
async def test_save_metric_stores_raw_json(db_session: AsyncSession) -> None:
    """raw_json alanı tam payload'un JSON dump'ını içerir."""
    server = await _seed_server(db_session)
    payload = MetricPayload(**_make_payload())

    metric = await metric_service.save_metric(db_session, server.id, payload)
    assert metric.raw_json is not None
    assert metric.raw_json["cpu"]["percent"] == pytest.approx(45.2)


@pytest.mark.asyncio
async def test_update_services_multiple(db_session: AsyncSession) -> None:
    """Birden fazla servis snapshot olarak kaydedilir."""
    server = await _seed_server(db_session)
    services = [
        ServiceData(name="nginx", status="active"),
        ServiceData(name="postgresql", status="active"),
        ServiceData(name="redis", status="failed", sub_state="dead"),
    ]

    records = await metric_service.update_services(db_session, server.id, services)
    assert len(records) == 3


@pytest.mark.asyncio
async def test_update_services_empty(db_session: AsyncSession) -> None:
    """Boş servis listesiyle flush yapılmaz, boş liste döner."""
    server = await _seed_server(db_session)
    records = await metric_service.update_services(db_session, server.id, [])
    assert records == []


@pytest.mark.asyncio
async def test_save_logs_respects_max_limit(db_session: AsyncSession) -> None:
    """200'den fazla log gönderilirse sadece 200 kaydedilir."""
    server = await _seed_server(db_session)
    now = datetime.now(UTC)
    logs = [
        LogData(
            source_file="/var/log/syslog",
            level="INFO",
            message=f"msg {i}",
            raw_line=f"raw {i}",
            logged_at=now,
        )
        for i in range(250)
    ]

    count = await metric_service.save_logs(db_session, server.id, logs)
    assert count == 200

    result = await db_session.execute(select(LogEntry))
    assert len(result.scalars().all()) == 200


@pytest.mark.asyncio
async def test_save_logs_under_limit(db_session: AsyncSession) -> None:
    """200'ün altında log gönderilirse hepsi kaydedilir."""
    server = await _seed_server(db_session)
    now = datetime.now(UTC)
    logs = [
        LogData(
            source_file="/var/log/syslog",
            level="ERROR",
            message=f"msg {i}",
            raw_line=f"raw {i}",
            logged_at=now,
        )
        for i in range(5)
    ]

    count = await metric_service.save_logs(db_session, server.id, logs)
    assert count == 5


@pytest.mark.asyncio
async def test_save_logs_empty(db_session: AsyncSession) -> None:
    """Boş log listesiyle 0 döner."""
    server = await _seed_server(db_session)
    count = await metric_service.save_logs(db_session, server.id, [])
    assert count == 0


# ===================================================================
# 4. Pydantic şema validation testleri
# ===================================================================


def test_payload_cpu_percent_above_100_rejected() -> None:
    """cpu.percent > 100 ile ValidationError fırlar."""
    data = _make_payload(cpu__percent=101.0)
    with pytest.raises(ValidationError):
        MetricPayload(**data)


def test_payload_cpu_percent_negative_rejected() -> None:
    """cpu.percent < 0 ile ValidationError fırlar."""
    data = _make_payload(cpu__percent=-1.0)
    with pytest.raises(ValidationError):
        MetricPayload(**data)


def test_payload_memory_negative_bytes_rejected() -> None:
    """Negatif memory bytes ile ValidationError fırlar."""
    data = _make_payload(memory__total_bytes=-100)
    with pytest.raises(ValidationError):
        MetricPayload(**data)


def test_payload_disk_percent_above_100_rejected() -> None:
    """disk.percent > 100 ile ValidationError fırlar."""
    data = _make_payload()
    data["disks"][0]["percent"] = 105.0
    with pytest.raises(ValidationError):
        MetricPayload(**data)


def test_payload_network_negative_bytes_rejected() -> None:
    """Negatif network bytes ile ValidationError fırlar."""
    data = _make_payload()
    data["networks"][0]["bytes_recv_per_sec"] = -10.0
    with pytest.raises(ValidationError):
        MetricPayload(**data)


def test_payload_extra_field_in_cpu_rejected() -> None:
    """CPU nesnesinde bilinmeyen field ile ValidationError (extra='forbid')."""
    data = _make_payload()
    data["cpu"]["unknown"] = 42
    with pytest.raises(ValidationError):
        MetricPayload(**data)


# ===================================================================
# 5. Alert engine testleri
# ===================================================================


@pytest.mark.asyncio
@patch("app.services.alert_engine.ai_analyzer.trigger_analysis", new_callable=AsyncMock)
async def test_alert_engine_critical_cpu(
    mock_ai: AsyncMock, db_session: AsyncSession,
) -> None:
    """CPU >= critical eşik → cpu_threshold alert oluşur."""
    server = await _seed_server(db_session)
    payload = MetricPayload(**_make_payload(cpu__percent=95.0))

    alerts = await alert_engine.check_thresholds(db_session, server.id, payload)
    await db_session.commit()

    cpu_alerts = [a for a in alerts if a.type == "cpu_threshold"]
    assert len(cpu_alerts) == 1
    assert cpu_alerts[0].severity == "critical"
    mock_ai.assert_called()


@pytest.mark.asyncio
@patch("app.services.alert_engine.ai_analyzer.trigger_analysis", new_callable=AsyncMock)
async def test_alert_engine_warning_cpu(
    mock_ai: AsyncMock, db_session: AsyncSession,
) -> None:
    """CPU >= warning ama < critical → warning severity alert."""
    server = await _seed_server(db_session)
    payload = MetricPayload(**_make_payload(cpu__percent=85.0))

    alerts = await alert_engine.check_thresholds(db_session, server.id, payload)
    await db_session.commit()

    cpu_alerts = [a for a in alerts if a.type == "cpu_threshold"]
    assert len(cpu_alerts) == 1
    assert cpu_alerts[0].severity == "warning"
    mock_ai.assert_not_called()


@pytest.mark.asyncio
@patch("app.services.alert_engine.ai_analyzer.trigger_analysis", new_callable=AsyncMock)
async def test_alert_engine_normal_cpu_no_alert(
    mock_ai: AsyncMock, db_session: AsyncSession,
) -> None:
    """CPU eşik altında → alert oluşmaz."""
    server = await _seed_server(db_session)
    payload = MetricPayload(**_make_payload(cpu__percent=45.0))

    alerts = await alert_engine.check_thresholds(db_session, server.id, payload)
    await db_session.commit()

    assert len([a for a in alerts if a.type == "cpu_threshold"]) == 0


@pytest.mark.asyncio
@patch("app.services.alert_engine.ai_analyzer.trigger_analysis", new_callable=AsyncMock)
async def test_alert_engine_duplicate_prevention(
    mock_ai: AsyncMock, db_session: AsyncSession,
) -> None:
    """Aynı tipte aktif alert varken yenisi oluşturulmaz (spam önleme)."""
    server = await _seed_server(db_session)
    payload = MetricPayload(**_make_payload(cpu__percent=95.0))

    alerts_1 = await alert_engine.check_thresholds(db_session, server.id, payload)
    await db_session.commit()
    assert len([a for a in alerts_1 if a.type == "cpu_threshold"]) == 1

    alerts_2 = await alert_engine.check_thresholds(db_session, server.id, payload)
    await db_session.commit()
    assert len([a for a in alerts_2 if a.type == "cpu_threshold"]) == 0

    total = await db_session.execute(
        select(Alert).where(Alert.type == "cpu_threshold")
    )
    assert len(total.scalars().all()) == 1


@pytest.mark.asyncio
@patch("app.services.alert_engine.ai_analyzer.trigger_analysis", new_callable=AsyncMock)
async def test_alert_engine_failed_service(
    mock_ai: AsyncMock, db_session: AsyncSession,
) -> None:
    """Failed servis → service_failed alert oluşur + AI tetiklenir."""
    server = await _seed_server(db_session)
    data = _make_payload()
    data["services"] = [{"name": "nginx", "status": "failed", "sub_state": "dead"}]
    payload = MetricPayload(**data)

    alerts = await alert_engine.check_thresholds(db_session, server.id, payload)
    await db_session.commit()

    svc_alerts = [a for a in alerts if a.type == "service_failed"]
    assert len(svc_alerts) == 1
    assert svc_alerts[0].severity == "critical"
    assert "nginx" in svc_alerts[0].message
    mock_ai.assert_called()


@pytest.mark.asyncio
@patch("app.services.alert_engine.ai_analyzer.trigger_analysis", new_callable=AsyncMock)
async def test_alert_engine_multiple_failed_services_single_alert(
    mock_ai: AsyncMock, db_session: AsyncSession,
) -> None:
    """Birden fazla failed servis olsa da aynı tipte tek alert oluşur (spam önleme)."""
    server = await _seed_server(db_session)
    data = _make_payload()
    data["services"] = [
        {"name": "nginx", "status": "failed", "sub_state": "dead"},
        {"name": "postgresql", "status": "failed", "sub_state": "dead"},
        {"name": "redis", "status": "active", "sub_state": "running"},
    ]
    payload = MetricPayload(**data)

    alerts = await alert_engine.check_thresholds(db_session, server.id, payload)
    await db_session.commit()

    svc_alerts = [a for a in alerts if a.type == "service_failed"]
    assert len(svc_alerts) == 1
    assert svc_alerts[0].severity == "critical"
    assert "nginx" in svc_alerts[0].message


@pytest.mark.asyncio
@patch("app.services.alert_engine.ai_analyzer.trigger_analysis", new_callable=AsyncMock)
async def test_alert_engine_critical_log_burst(
    mock_ai: AsyncMock, db_session: AsyncSession,
) -> None:
    """5+ ERROR log → critical_log_burst warning alert oluşur."""
    server = await _seed_server(db_session)
    data = _make_payload()
    data["log_entries"] = [
        {
            "source_file": "/var/log/syslog",
            "level": "ERROR",
            "message": f"error {i}",
            "raw_line": f"Mar 11 12:00:00 host: error {i}",
            "logged_at": "2026-03-11T12:00:00Z",
        }
        for i in range(6)
    ]
    payload = MetricPayload(**data)

    alerts = await alert_engine.check_thresholds(db_session, server.id, payload)
    await db_session.commit()

    log_alerts = [a for a in alerts if a.type == "critical_log_burst"]
    assert len(log_alerts) == 1
    assert log_alerts[0].severity == "warning"


@pytest.mark.asyncio
@patch("app.services.alert_engine.ai_analyzer.trigger_analysis", new_callable=AsyncMock)
async def test_alert_engine_4_error_logs_no_alert(
    mock_ai: AsyncMock, db_session: AsyncSession,
) -> None:
    """4 ERROR log → eşik altı, critical_log_burst alert oluşmaz."""
    server = await _seed_server(db_session)
    data = _make_payload()
    data["log_entries"] = [
        {
            "source_file": "/var/log/syslog",
            "level": "ERROR",
            "message": f"error {i}",
            "raw_line": f"raw {i}",
            "logged_at": "2026-03-11T12:00:00Z",
        }
        for i in range(4)
    ]
    payload = MetricPayload(**data)

    alerts = await alert_engine.check_thresholds(db_session, server.id, payload)
    await db_session.commit()

    assert len([a for a in alerts if a.type == "critical_log_burst"]) == 0


@pytest.mark.asyncio
@patch("app.services.alert_engine.ai_analyzer.trigger_analysis", new_callable=AsyncMock)
async def test_alert_engine_ram_critical(
    mock_ai: AsyncMock, db_session: AsyncSession,
) -> None:
    """RAM >= critical eşik → ram_threshold alert oluşur."""
    server = await _seed_server(db_session)
    payload = MetricPayload(**_make_payload(memory__percent=97.0))

    alerts = await alert_engine.check_thresholds(db_session, server.id, payload)
    await db_session.commit()

    ram_alerts = [a for a in alerts if a.type == "ram_threshold"]
    assert len(ram_alerts) == 1
    assert ram_alerts[0].severity == "critical"


@pytest.mark.asyncio
@patch("app.services.alert_engine.ai_analyzer.trigger_analysis", new_callable=AsyncMock)
async def test_alert_engine_disk_critical(
    mock_ai: AsyncMock, db_session: AsyncSession,
) -> None:
    """Disk >= critical eşik → disk_threshold alert oluşur."""
    server = await _seed_server(db_session)
    data = _make_payload()
    data["disks"][0]["percent"] = 96.0
    payload = MetricPayload(**data)

    alerts = await alert_engine.check_thresholds(db_session, server.id, payload)
    await db_session.commit()

    disk_alerts = [a for a in alerts if a.type == "disk_threshold"]
    assert len(disk_alerts) == 1
    assert disk_alerts[0].severity == "critical"


@pytest.mark.asyncio
@patch("app.services.alert_engine.ai_analyzer.trigger_analysis", new_callable=AsyncMock)
async def test_alert_engine_all_metrics_simultaneous(
    mock_ai: AsyncMock, db_session: AsyncSession,
) -> None:
    """CPU + RAM + Disk hepsi kritik → 3 ayrı alert oluşur."""
    server = await _seed_server(db_session)
    data = _make_payload(cpu__percent=95.0, memory__percent=97.0)
    data["disks"][0]["percent"] = 96.0
    payload = MetricPayload(**data)

    alerts = await alert_engine.check_thresholds(db_session, server.id, payload)
    await db_session.commit()

    types = {a.type for a in alerts}
    assert "cpu_threshold" in types
    assert "ram_threshold" in types
    assert "disk_threshold" in types
    assert len(alerts) == 3


@pytest.mark.asyncio
@patch("app.services.alert_engine.ai_analyzer.trigger_analysis", new_callable=AsyncMock)
async def test_alert_engine_cpu_boundary_at_exact_warning(
    mock_ai: AsyncMock, db_session: AsyncSession,
) -> None:
    """CPU tam warning eşiğinde (80.0) → warning alert oluşur."""
    server = await _seed_server(db_session)
    payload = MetricPayload(**_make_payload(cpu__percent=80.0))

    alerts = await alert_engine.check_thresholds(db_session, server.id, payload)
    await db_session.commit()

    cpu_alerts = [a for a in alerts if a.type == "cpu_threshold"]
    assert len(cpu_alerts) == 1
    assert cpu_alerts[0].severity == "warning"


@pytest.mark.asyncio
@patch("app.services.alert_engine.ai_analyzer.trigger_analysis", new_callable=AsyncMock)
async def test_alert_engine_cpu_just_below_warning(
    mock_ai: AsyncMock, db_session: AsyncSession,
) -> None:
    """CPU warning eşiğinin hemen altında (79.9) → alert yok."""
    server = await _seed_server(db_session)
    payload = MetricPayload(**_make_payload(cpu__percent=79.9))

    alerts = await alert_engine.check_thresholds(db_session, server.id, payload)
    await db_session.commit()

    assert len([a for a in alerts if a.type == "cpu_threshold"]) == 0
