"""Alert endpoint + alert_service + auto-resolve testleri."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.security import hash_api_key
from app.models.alert import Alert
from app.models.server import Server
from app.schemas.metric import MetricPayload
from app.services import alert_engine, alert_service
from app.services.alert_service import AlertFilters

# ===================================================================
# Seed helpers
# ===================================================================

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
    "top_processes": [],
    "services": [],
    "log_entries": [],
}


async def _seed_server(db: AsyncSession, name: str = "srv-01") -> Server:
    server = Server(
        name=name,
        hostname=f"{name}.local",
        ip_address="10.0.0.1",
        api_key=hash_api_key(f"key-{name}"),
        status="active",
    )
    db.add(server)
    await db.commit()
    await db.refresh(server)
    return server


async def _seed_alert(
    db: AsyncSession,
    server_id: int,
    *,
    alert_type: str = "cpu_threshold",
    severity: str = "warning",
    message: str = "CPU yüksek",
    resolved: bool = False,
) -> Alert:
    alert = Alert(
        server_id=server_id,
        type=alert_type,
        severity=severity,
        message=message,
    )
    if resolved:
        alert.resolved_at = datetime.now(UTC)
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert


def _make_payload(**overrides: object) -> dict:
    data = deepcopy(SAMPLE_PAYLOAD)
    for key, val in overrides.items():
        keys = key.split("__")
        target = data
        for k in keys[:-1]:
            target = target[k]
        target[keys[-1]] = val
    return data


# ===================================================================
# 1. GET /alerts — listeleme
# ===================================================================


@pytest.mark.asyncio
async def test_list_alerts_empty(client: AsyncClient, auth_headers: dict) -> None:
    """Alert yokken boş liste döner."""
    resp = await client.get("/api/v1/alerts", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"] == []
    assert body["meta"]["total"] == 0


@pytest.mark.asyncio
async def test_list_alerts_with_data(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict,
) -> None:
    """Alert varken listeyi döner."""
    server = await _seed_server(db_session)
    await _seed_alert(db_session, server.id)
    await _seed_alert(
        db_session, server.id,
        alert_type="ram_threshold", severity="critical", message="RAM kritik",
    )

    resp = await client.get("/api/v1/alerts", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["meta"]["total"] == 2
    assert len(body["data"]) == 2


@pytest.mark.asyncio
async def test_list_alerts_response_format(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict,
) -> None:
    """Alert yanıtı standart {data, meta} formatına ve doğru alanlara sahip."""
    server = await _seed_server(db_session)
    await _seed_alert(db_session, server.id)

    resp = await client.get("/api/v1/alerts", headers=auth_headers)
    body = resp.json()
    assert "data" in body
    assert "meta" in body
    alert = body["data"][0]
    assert set(alert.keys()) == {
        "id",
        "server_id",
        "type",
        "dedupe_key",
        "severity",
        "message",
        "resolved_at",
        "created_at",
    }


@pytest.mark.asyncio
async def test_list_alerts_no_auth(client: AsyncClient) -> None:
    """Token olmadan 401 döner."""
    resp = await client.get("/api/v1/alerts")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_alerts_filter_severity(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict,
) -> None:
    """Severity filtresi çalışır."""
    server = await _seed_server(db_session)
    await _seed_alert(db_session, server.id, severity="warning")
    await _seed_alert(
        db_session, server.id,
        alert_type="ram_threshold", severity="critical", message="RAM",
    )

    resp = await client.get(
        "/api/v1/alerts", params={"severity": "critical"}, headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["meta"]["total"] == 1
    assert body["data"][0]["severity"] == "critical"


@pytest.mark.asyncio
async def test_list_alerts_filter_type(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict,
) -> None:
    """Alert type filtresi çalışır."""
    server = await _seed_server(db_session)
    await _seed_alert(db_session, server.id, alert_type="cpu_threshold")
    await _seed_alert(db_session, server.id, alert_type="ram_threshold", message="RAM")
    await _seed_alert(db_session, server.id, alert_type="disk_threshold", message="Disk")

    resp = await client.get(
        "/api/v1/alerts", params={"alert_type": "ram_threshold"}, headers=auth_headers,
    )
    body = resp.json()
    assert body["meta"]["total"] == 1
    assert body["data"][0]["type"] == "ram_threshold"


@pytest.mark.asyncio
async def test_list_alerts_filter_server_id(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict,
) -> None:
    """server_id filtresi çalışır."""
    srv1 = await _seed_server(db_session, "srv-01")
    srv2 = await _seed_server(db_session, "srv-02")
    await _seed_alert(db_session, srv1.id)
    await _seed_alert(db_session, srv1.id, alert_type="ram_threshold", message="RAM")
    await _seed_alert(db_session, srv2.id, message="başka sunucu")

    resp = await client.get(
        "/api/v1/alerts", params={"server_id": srv1.id}, headers=auth_headers,
    )
    body = resp.json()
    assert body["meta"]["total"] == 2


@pytest.mark.asyncio
async def test_list_alerts_filter_resolved(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict,
) -> None:
    """resolved=true/false filtresi çalışır."""
    server = await _seed_server(db_session)
    await _seed_alert(db_session, server.id, resolved=False)
    await _seed_alert(
        db_session, server.id,
        alert_type="ram_threshold", message="RAM", resolved=True,
    )

    resp_active = await client.get(
        "/api/v1/alerts", params={"resolved": "false"}, headers=auth_headers,
    )
    assert resp_active.json()["meta"]["total"] == 1
    assert resp_active.json()["data"][0]["resolved_at"] is None

    resp_resolved = await client.get(
        "/api/v1/alerts", params={"resolved": "true"}, headers=auth_headers,
    )
    assert resp_resolved.json()["meta"]["total"] == 1
    assert resp_resolved.json()["data"][0]["resolved_at"] is not None


@pytest.mark.asyncio
async def test_list_alerts_combined_endpoint_filters(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict,
) -> None:
    """severity + server_id kombine filtre endpoint üzerinden çalışır."""
    srv1 = await _seed_server(db_session, "srv-01")
    srv2 = await _seed_server(db_session, "srv-02")
    await _seed_alert(db_session, srv1.id, severity="critical")
    await _seed_alert(db_session, srv1.id, severity="warning", alert_type="ram_threshold", message="RAM")
    await _seed_alert(db_session, srv2.id, severity="critical", message="başka")

    resp = await client.get(
        "/api/v1/alerts",
        params={"severity": "critical", "server_id": srv1.id},
        headers=auth_headers,
    )
    body = resp.json()
    assert body["meta"]["total"] == 1
    assert body["data"][0]["severity"] == "critical"
    assert body["data"][0]["server_id"] == srv1.id


@pytest.mark.asyncio
async def test_list_alerts_pagination(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict,
) -> None:
    """Sayfalama doğru çalışır."""
    server = await _seed_server(db_session)
    for i in range(5):
        await _seed_alert(db_session, server.id, message=f"alert-{i}")

    resp1 = await client.get(
        "/api/v1/alerts", params={"page": 1, "per_page": 2}, headers=auth_headers,
    )
    body1 = resp1.json()
    assert len(body1["data"]) == 2
    assert body1["meta"]["total"] == 5
    assert body1["meta"]["page"] == 1

    resp2 = await client.get(
        "/api/v1/alerts", params={"page": 3, "per_page": 2}, headers=auth_headers,
    )
    assert len(resp2.json()["data"]) == 1


@pytest.mark.asyncio
async def test_list_alerts_ordered_desc(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict,
) -> None:
    """Alert'ler created_at DESC sıralı döner."""
    server = await _seed_server(db_session)
    for i in range(3):
        await _seed_alert(db_session, server.id, message=f"alert-{i}")

    resp = await client.get("/api/v1/alerts", headers=auth_headers)
    timestamps = [d["created_at"] for d in resp.json()["data"]]
    assert timestamps == sorted(timestamps, reverse=True)


# ===================================================================
# 2. PATCH /alerts/{id}/resolve
# ===================================================================


@pytest.mark.asyncio
async def test_resolve_alert(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict,
) -> None:
    """Alert çözümleme resolved_at alanını doldurur."""
    server = await _seed_server(db_session)
    alert = await _seed_alert(db_session, server.id)

    resp = await client.patch(f"/api/v1/alerts/{alert.id}/resolve", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["resolved_at"] is not None
    assert "timestamp" in body["meta"]


@pytest.mark.asyncio
async def test_resolve_already_resolved_idempotent(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict,
) -> None:
    """Zaten çözülmüş alert'i tekrar resolve etmek hata vermez (idempotent)."""
    server = await _seed_server(db_session)
    alert = await _seed_alert(db_session, server.id, resolved=True)
    original_ts = alert.resolved_at

    resp = await client.patch(f"/api/v1/alerts/{alert.id}/resolve", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["resolved_at"] is not None
    await db_session.refresh(alert)
    assert alert.resolved_at == original_ts


@pytest.mark.asyncio
async def test_resolve_alert_not_found(client: AsyncClient, auth_headers: dict) -> None:
    """Olmayan alert için 404 döner."""
    resp = await client.patch("/api/v1/alerts/9999/resolve", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_resolve_alert_no_auth(client: AsyncClient) -> None:
    """Token olmadan 401 döner."""
    resp = await client.patch("/api/v1/alerts/1/resolve")
    assert resp.status_code == 401


# ===================================================================
# 3. GET /alerts/stats
# ===================================================================


@pytest.mark.asyncio
async def test_alert_stats_empty(client: AsyncClient, auth_headers: dict) -> None:
    """Alert yokken tüm sayaçlar 0."""
    resp = await client.get("/api/v1/alerts/stats", headers=auth_headers)
    assert resp.status_code == 200
    stats = resp.json()["data"]
    assert stats["total_active"] == 0
    assert stats["critical"] == 0
    assert stats["warning"] == 0


@pytest.mark.asyncio
async def test_alert_stats_counts(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict,
) -> None:
    """Aktif alert'lerin severity bazlı sayıları doğru döner."""
    server = await _seed_server(db_session)
    await _seed_alert(db_session, server.id, severity="warning")
    await _seed_alert(db_session, server.id, alert_type="ram_threshold", severity="critical", message="RAM")
    await _seed_alert(db_session, server.id, alert_type="disk_threshold", severity="critical", message="Disk")
    await _seed_alert(
        db_session, server.id,
        alert_type="old", severity="warning", message="eski", resolved=True,
    )

    resp = await client.get("/api/v1/alerts/stats", headers=auth_headers)
    stats = resp.json()["data"]
    assert stats["total_active"] == 3
    assert stats["critical"] == 2
    assert stats["warning"] == 1


@pytest.mark.asyncio
async def test_alert_stats_excludes_resolved(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict,
) -> None:
    """Çözümlenen alert'ler stats'a dahil edilmez."""
    server = await _seed_server(db_session)
    await _seed_alert(db_session, server.id, severity="critical", resolved=True)
    await _seed_alert(db_session, server.id, alert_type="ram", severity="critical", message="RAM", resolved=True)

    resp = await client.get("/api/v1/alerts/stats", headers=auth_headers)
    stats = resp.json()["data"]
    assert stats["total_active"] == 0


@pytest.mark.asyncio
async def test_alert_stats_server_filter(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict,
) -> None:
    """server_id ile filtrelenmiş istatistik doğru döner."""
    srv1 = await _seed_server(db_session, "srv-01")
    srv2 = await _seed_server(db_session, "srv-02")
    await _seed_alert(db_session, srv1.id, severity="critical")
    await _seed_alert(db_session, srv2.id, severity="warning", message="başka")

    resp = await client.get(
        "/api/v1/alerts/stats", params={"server_id": srv1.id}, headers=auth_headers,
    )
    stats = resp.json()["data"]
    assert stats["total_active"] == 1
    assert stats["critical"] == 1
    assert stats["warning"] == 0


@pytest.mark.asyncio
async def test_alert_stats_no_auth(client: AsyncClient) -> None:
    """Token olmadan 401 döner."""
    resp = await client.get("/api/v1/alerts/stats")
    assert resp.status_code == 401


# ===================================================================
# 4. alert_service unit testleri
# ===================================================================


@pytest.mark.asyncio
async def test_service_list_combined_filters(db_session: AsyncSession) -> None:
    """AlertFilters birden fazla filtre kombinasyonunu doğru uygular."""
    server = await _seed_server(db_session)
    await _seed_alert(db_session, server.id, severity="critical")
    await _seed_alert(db_session, server.id, severity="warning", alert_type="ram_threshold", message="RAM")
    await _seed_alert(db_session, server.id, severity="critical", alert_type="disk_threshold", message="Disk", resolved=True)

    filters = AlertFilters(severity="critical", resolved=False)
    alerts, total = await alert_service.list_alerts(db_session, filters)
    assert total == 1
    assert alerts[0].severity == "critical"
    assert alerts[0].resolved_at is None


@pytest.mark.asyncio
async def test_service_list_type_and_server_filter(db_session: AsyncSession) -> None:
    """alert_type + server_id kombinasyonu doğru çalışır."""
    srv1 = await _seed_server(db_session, "srv-01")
    srv2 = await _seed_server(db_session, "srv-02")
    await _seed_alert(db_session, srv1.id, alert_type="cpu_threshold")
    await _seed_alert(db_session, srv1.id, alert_type="ram_threshold", message="RAM")
    await _seed_alert(db_session, srv2.id, alert_type="cpu_threshold", message="başka cpu")

    filters = AlertFilters(server_id=srv1.id, alert_type="cpu_threshold")
    alerts, total = await alert_service.list_alerts(db_session, filters)
    assert total == 1
    assert alerts[0].server_id == srv1.id


@pytest.mark.asyncio
async def test_service_get_alert_or_404_found(db_session: AsyncSession) -> None:
    """Mevcut alert'i döndürür."""
    server = await _seed_server(db_session)
    alert = await _seed_alert(db_session, server.id)

    found = await alert_service.get_alert_or_404(db_session, alert.id)
    assert found.id == alert.id


@pytest.mark.asyncio
async def test_service_get_alert_or_404_not_found(db_session: AsyncSession) -> None:
    """Olmayan alert için NotFoundError fırlatır."""
    with pytest.raises(NotFoundError):
        await alert_service.get_alert_or_404(db_session, 9999)


@pytest.mark.asyncio
async def test_service_resolve_sets_timestamp(db_session: AsyncSession) -> None:
    """resolve_alert resolved_at'ı doldurur."""
    server = await _seed_server(db_session)
    alert = await _seed_alert(db_session, server.id)
    assert alert.resolved_at is None

    resolved = await alert_service.resolve_alert(db_session, alert.id)
    assert resolved.resolved_at is not None


@pytest.mark.asyncio
async def test_service_resolve_idempotent(db_session: AsyncSession) -> None:
    """Zaten çözülmüş alert'in resolved_at değeri değişmez."""
    server = await _seed_server(db_session)
    alert = await _seed_alert(db_session, server.id, resolved=True)
    original = alert.resolved_at

    resolved = await alert_service.resolve_alert(db_session, alert.id)
    assert resolved.resolved_at == original


@pytest.mark.asyncio
async def test_service_auto_resolve_by_type(db_session: AsyncSession) -> None:
    """auto_resolve_by_type aktif alert'leri toplu çözümler."""
    server = await _seed_server(db_session)
    await _seed_alert(db_session, server.id, alert_type="cpu_threshold")
    await _seed_alert(db_session, server.id, alert_type="cpu_threshold", severity="critical", message="CPU kritik")
    await _seed_alert(db_session, server.id, alert_type="ram_threshold", message="RAM yüksek")

    count = await alert_service.auto_resolve_by_type(db_session, server.id, "cpu_threshold")
    await db_session.commit()
    assert count == 2

    result = await db_session.execute(
        select(Alert).where(Alert.type == "cpu_threshold")
    )
    for a in result.scalars().all():
        assert a.resolved_at is not None

    ram = await db_session.execute(
        select(Alert).where(Alert.type == "ram_threshold")
    )
    assert ram.scalar_one().resolved_at is None


@pytest.mark.asyncio
async def test_service_auto_resolve_no_active(db_session: AsyncSession) -> None:
    """Aktif alert yoksa auto_resolve 0 döner."""
    server = await _seed_server(db_session)
    count = await alert_service.auto_resolve_by_type(db_session, server.id, "cpu_threshold")
    assert count == 0


@pytest.mark.asyncio
async def test_service_auto_resolve_skips_already_resolved(db_session: AsyncSession) -> None:
    """Zaten çözülmüş alert'ler auto_resolve'dan etkilenmez."""
    server = await _seed_server(db_session)
    await _seed_alert(db_session, server.id, alert_type="cpu_threshold", resolved=True)

    count = await alert_service.auto_resolve_by_type(db_session, server.id, "cpu_threshold")
    assert count == 0


@pytest.mark.asyncio
async def test_service_stats_with_mixed_data(db_session: AsyncSession) -> None:
    """get_stats aktif ve çözümlü karışık veriyle doğru çalışır."""
    server = await _seed_server(db_session)
    await _seed_alert(db_session, server.id, severity="warning")
    await _seed_alert(db_session, server.id, severity="critical", alert_type="ram", message="RAM")
    await _seed_alert(db_session, server.id, severity="critical", alert_type="disk", message="Disk", resolved=True)

    stats = await alert_service.get_stats(db_session)
    assert stats["total_active"] == 2
    assert stats["critical"] == 1
    assert stats["warning"] == 1


# ===================================================================
# 5. alert_engine auto-resolve entegrasyonu
# ===================================================================


@pytest.mark.asyncio
@patch("app.services.alert_engine.ai_analyzer.trigger_analysis", new_callable=AsyncMock)
async def test_engine_auto_resolves_cpu_when_normal(
    mock_ai: AsyncMock, db_session: AsyncSession,
) -> None:
    """CPU eşik altına düşünce mevcut cpu_threshold alert'leri otomatik çözümlenir."""
    server = await _seed_server(db_session)

    high = MetricPayload(**_make_payload(cpu__percent=95.0))
    alerts = await alert_engine.check_thresholds(db_session, server.id, high)
    await db_session.commit()
    assert len([a for a in alerts if a.type == "cpu_threshold"]) == 1

    normal = MetricPayload(**_make_payload(cpu__percent=30.0))
    await alert_engine.check_thresholds(db_session, server.id, normal)
    await db_session.commit()

    result = await db_session.execute(
        select(Alert).where(Alert.type == "cpu_threshold")
    )
    for a in result.scalars().all():
        assert a.resolved_at is not None


@pytest.mark.asyncio
@patch("app.services.alert_engine.ai_analyzer.trigger_analysis", new_callable=AsyncMock)
async def test_engine_auto_resolves_ram_when_normal(
    mock_ai: AsyncMock, db_session: AsyncSession,
) -> None:
    """RAM eşik altına düşünce mevcut ram_threshold alert'leri otomatik çözümlenir."""
    server = await _seed_server(db_session)

    high = MetricPayload(**_make_payload(memory__percent=97.0))
    await alert_engine.check_thresholds(db_session, server.id, high)
    await db_session.commit()

    normal = MetricPayload(**_make_payload(memory__percent=40.0))
    await alert_engine.check_thresholds(db_session, server.id, normal)
    await db_session.commit()

    result = await db_session.execute(
        select(Alert).where(Alert.type == "ram_threshold")
    )
    for a in result.scalars().all():
        assert a.resolved_at is not None


@pytest.mark.asyncio
@patch("app.services.alert_engine.ai_analyzer.trigger_analysis", new_callable=AsyncMock)
async def test_engine_auto_resolves_disk_when_normal(
    mock_ai: AsyncMock, db_session: AsyncSession,
) -> None:
    """Disk eşik altına düşünce mevcut disk_threshold alert'leri otomatik çözümlenir."""
    server = await _seed_server(db_session)

    high_data = _make_payload()
    high_data["disks"][0]["percent"] = 96.0
    await alert_engine.check_thresholds(
        db_session, server.id, MetricPayload(**high_data),
    )
    await db_session.commit()

    normal_data = _make_payload()
    normal_data["disks"][0]["percent"] = 50.0
    await alert_engine.check_thresholds(
        db_session, server.id, MetricPayload(**normal_data),
    )
    await db_session.commit()

    result = await db_session.execute(
        select(Alert).where(Alert.type == "disk_threshold")
    )
    for a in result.scalars().all():
        assert a.resolved_at is not None


@pytest.mark.asyncio
@patch("app.services.alert_engine.ai_analyzer.trigger_analysis", new_callable=AsyncMock)
async def test_engine_warning_to_critical_escalation(
    mock_ai: AsyncMock, db_session: AsyncSession,
) -> None:
    """CPU warning alert aktifken critical'a yükselince mevcut alert güncellenir."""
    server = await _seed_server(db_session)

    warn = MetricPayload(**_make_payload(cpu__percent=85.0))
    alerts_w = await alert_engine.check_thresholds(db_session, server.id, warn)
    await db_session.commit()
    assert len([a for a in alerts_w if a.type == "cpu_threshold"]) == 1

    crit = MetricPayload(**_make_payload(cpu__percent=95.0))
    alerts_c = await alert_engine.check_thresholds(db_session, server.id, crit)
    await db_session.commit()
    cpu_alerts = [a for a in alerts_c if a.type == "cpu_threshold"]
    assert len(cpu_alerts) == 1
    assert cpu_alerts[0].severity == "critical"
    mock_ai.assert_called_once()

    total = await db_session.execute(
        select(Alert).where(Alert.type == "cpu_threshold", Alert.resolved_at.is_(None))
    )
    assert len(total.scalars().all()) == 1


@pytest.mark.asyncio
@patch("app.services.alert_engine.ai_analyzer.trigger_analysis", new_callable=AsyncMock)
async def test_engine_resolve_then_new_alert(
    mock_ai: AsyncMock, db_session: AsyncSession,
) -> None:
    """CPU kritik → normale dön (auto-resolve) → tekrar kritik → yeni alert oluşur."""
    server = await _seed_server(db_session)

    high = MetricPayload(**_make_payload(cpu__percent=95.0))
    await alert_engine.check_thresholds(db_session, server.id, high)
    await db_session.commit()

    normal = MetricPayload(**_make_payload(cpu__percent=30.0))
    await alert_engine.check_thresholds(db_session, server.id, normal)
    await db_session.commit()

    high2 = MetricPayload(**_make_payload(cpu__percent=92.0))
    alerts2 = await alert_engine.check_thresholds(db_session, server.id, high2)
    await db_session.commit()
    assert len([a for a in alerts2 if a.type == "cpu_threshold"]) == 1

    result = await db_session.execute(
        select(Alert).where(Alert.type == "cpu_threshold")
    )
    all_alerts = result.scalars().all()
    assert len(all_alerts) == 2
    resolved = [a for a in all_alerts if a.resolved_at is not None]
    active = [a for a in all_alerts if a.resolved_at is None]
    assert len(resolved) == 1
    assert len(active) == 1
