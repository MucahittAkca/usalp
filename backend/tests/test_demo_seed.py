"""Demo seed verisi testleri."""

from __future__ import annotations

import json

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_analysis import AIAnalysis
from app.models.alert import Alert
from app.models.log_entry import LogEntry
from app.models.metric import Metric
from app.models.server import Server
from app.models.service_status import ServiceStatus
from app.services.demo_seed import DEMO_API_KEY_PREFIX, seed_demo_data


@pytest.mark.asyncio
async def test_seed_demo_data_creates_representative_dataset(
    db_session: AsyncSession,
) -> None:
    """Demo seed dashboard'un ana yüzeylerini dolduracak veri üretir."""
    result = await seed_demo_data(db_session, reset=True)
    await db_session.commit()

    assert result.servers == 4
    assert result.metrics > 400
    assert result.logs == 72
    assert result.services >= 10
    assert result.alerts >= 4
    assert result.analyses == 2

    demo_server_count = await db_session.scalar(
        select(func.count(Server.id)).where(Server.api_key.like(f"{DEMO_API_KEY_PREFIX}%"))
    )
    assert demo_server_count == 4

    web = await db_session.scalar(select(Server).where(Server.name == "prod-web-01"))
    assert web is not None
    assert web.environment == "production"
    assert web.group_name == "edge"
    assert web.status == "warning"
    assert "critical" in web.tags

    active_alerts = await db_session.scalar(
        select(func.count(Alert.id)).where(Alert.resolved_at.is_(None))
    )
    assert active_alerts == 3

    analysis = await db_session.scalar(
        select(AIAnalysis)
        .join(Server, AIAnalysis.server_id == Server.id)
        .where(Server.name == "prod-db-01")
    )
    assert analysis is not None
    evidence_lines = json.loads(analysis.evidence_lines)
    commands = json.loads(analysis.commands)

    assert any("No space left on device" in line for line in evidence_lines)
    assert any(command["risk_level"] == "high" for command in commands)


@pytest.mark.asyncio
async def test_seed_demo_data_reset_is_idempotent_and_preserves_user_data(
    db_session: AsyncSession,
) -> None:
    """Reset yalnızca demo prefix'li veriyi yeniler; manuel kayıtları korur."""
    user_server = Server(
        name="user-server",
        hostname="user-server.local",
        ip_address="192.0.2.10",
        api_key="user-owned-key",
        environment="production",
        group_name="custom",
        tags=["manual"],
        status="online",
    )
    db_session.add(user_server)
    await db_session.commit()

    first = await seed_demo_data(db_session, reset=True)
    await db_session.commit()
    second = await seed_demo_data(db_session, reset=True)
    await db_session.commit()

    assert second == first

    total_servers = await db_session.scalar(select(func.count(Server.id)))
    demo_servers = await db_session.scalar(
        select(func.count(Server.id)).where(Server.api_key.like(f"{DEMO_API_KEY_PREFIX}%"))
    )
    demo_metrics = await db_session.scalar(
        select(func.count(Metric.id))
        .join(Server, Metric.server_id == Server.id)
        .where(Server.api_key.like(f"{DEMO_API_KEY_PREFIX}%"))
    )
    demo_logs = await db_session.scalar(
        select(func.count(LogEntry.id))
        .join(Server, LogEntry.server_id == Server.id)
        .where(Server.api_key.like(f"{DEMO_API_KEY_PREFIX}%"))
    )
    demo_services = await db_session.scalar(
        select(func.count(ServiceStatus.id))
        .join(Server, ServiceStatus.server_id == Server.id)
        .where(Server.api_key.like(f"{DEMO_API_KEY_PREFIX}%"))
    )

    assert total_servers == 5
    assert demo_servers == 4
    assert demo_metrics == second.metrics
    assert demo_logs == second.logs
    assert demo_services == second.services

    skipped = await seed_demo_data(db_session, reset=False)
    assert skipped.skipped is True
