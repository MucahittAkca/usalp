"""Demo seed verisi testleri."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_api_key, is_hashed_api_key
from app.models.ai_analysis import AIAnalysis
from app.models.alert import Alert
from app.models.log_entry import LogEntry
from app.models.metric import Metric
from app.models.server import Server
from app.models.service_status import ServiceStatus
from app.services import server_status
from app.services.demo_seed import DEMO_HOST_SUFFIX, seed_demo_data


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
        select(func.count(Server.id)).where(Server.hostname.like(f"%{DEMO_HOST_SUFFIX}"))
    )
    assert demo_server_count == 4

    web = await db_session.scalar(select(Server).where(Server.name == "prod-web-01"))
    assert web is not None
    assert web.environment == "production"
    assert web.group_name == "edge"
    assert web.status == "warning"
    assert "critical" in web.tags
    assert is_hashed_api_key(web.api_key)

    active_alerts = await db_session.scalar(
        select(func.count(Alert.id)).where(Alert.resolved_at.is_(None))
    )
    assert active_alerts == 3

    assert (
        await db_session.scalar(
            select(func.count(Alert.id)).join(Server, Alert.server_id == Server.id)
        )
    ) == result.alerts

    analysis = await db_session.scalar(
        select(AIAnalysis)
        .join(Server, AIAnalysis.server_id == Server.id)
        .where(Server.name == "prod-db-01")
    )
    assert analysis is not None
    assert "[DEMO]" in analysis.summary
    assert "No space left on device" in analysis.evidence_lines
    assert "df -h /var/lib/postgresql" in analysis.commands


@pytest.mark.asyncio
async def test_seed_demo_data_reset_is_idempotent_and_preserves_user_data(
    db_session: AsyncSession,
) -> None:
    """Reset yalnızca demo suffix'li veriyi yeniler; manuel kayıtları korur."""
    user_server = Server(
        name="user-server",
        hostname="user-server.local",
        ip_address="192.0.2.10",
        api_key=hash_api_key("user-owned-key"),
        environment="production",
        group_name="custom",
        tags=["manual"],
        status="online",
    )
    db_session.add(user_server)
    await db_session.commit()

    first = await seed_demo_data(db_session, reset=True)
    await db_session.commit()
    first_ids = list(
        (
            await db_session.execute(
                select(Server.id)
                .where(Server.hostname.like(f"%{DEMO_HOST_SUFFIX}"))
                .order_by(Server.hostname)
            )
        ).scalars()
    )
    second = await seed_demo_data(db_session, reset=True)
    await db_session.commit()
    second_ids = list(
        (
            await db_session.execute(
                select(Server.id)
                .where(Server.hostname.like(f"%{DEMO_HOST_SUFFIX}"))
                .order_by(Server.hostname)
            )
        ).scalars()
    )

    assert second == first
    assert second_ids == first_ids

    first_reference = await db_session.scalar(
        select(func.max(Metric.recorded_at))
        .join(Server, Metric.server_id == Server.id)
        .where(Server.hostname.like(f"%{DEMO_HOST_SUFFIX}"))
    )
    await seed_demo_data(db_session, reset=True)
    await db_session.commit()
    second_reference = await db_session.scalar(
        select(func.max(Metric.recorded_at))
        .join(Server, Metric.server_id == Server.id)
        .where(Server.hostname.like(f"%{DEMO_HOST_SUFFIX}"))
    )
    assert second_reference == first_reference

    total_servers = await db_session.scalar(select(func.count(Server.id)))
    demo_servers = await db_session.scalar(
        select(func.count(Server.id)).where(Server.hostname.like(f"%{DEMO_HOST_SUFFIX}"))
    )
    demo_metrics = await db_session.scalar(
        select(func.count(Metric.id))
        .join(Server, Metric.server_id == Server.id)
        .where(Server.hostname.like(f"%{DEMO_HOST_SUFFIX}"))
    )
    demo_logs = await db_session.scalar(
        select(func.count(LogEntry.id))
        .join(Server, LogEntry.server_id == Server.id)
        .where(Server.hostname.like(f"%{DEMO_HOST_SUFFIX}"))
    )
    demo_services = await db_session.scalar(
        select(func.count(ServiceStatus.id))
        .join(Server, ServiceStatus.server_id == Server.id)
        .where(Server.hostname.like(f"%{DEMO_HOST_SUFFIX}"))
    )

    assert total_servers == 5
    assert demo_servers == 4
    assert demo_metrics == second.metrics
    assert demo_logs == second.logs
    assert demo_services == second.services

    skipped = await seed_demo_data(db_session, reset=False)
    assert skipped.skipped is True


@pytest.mark.asyncio
async def test_stale_maintenance_does_not_flip_demo_servers_offline(
    db_session: AsyncSession,
) -> None:
    """Demo sunucular F5/bakım döngüsüyle offline'a düşmez."""
    old_last_seen = datetime.now(UTC) - timedelta(days=1)
    demo_server = Server(
        name="demo-web",
        hostname=f"demo-web{DEMO_HOST_SUFFIX}",
        ip_address="10.20.0.99",
        api_key=hash_api_key("demo-key"),
        environment="production",
        group_name="edge",
        tags=["demo"],
        status="warning",
        last_seen=old_last_seen,
    )
    user_server = Server(
        name="user-web",
        hostname="user-web.local",
        ip_address="192.0.2.11",
        api_key=hash_api_key("user-key"),
        environment="production",
        group_name="edge",
        tags=["manual"],
        status="online",
        last_seen=old_last_seen,
    )
    db_session.add_all([demo_server, user_server])
    await db_session.commit()

    changed = await server_status.mark_stale_servers_offline(db_session)
    await db_session.commit()
    await db_session.refresh(demo_server)
    await db_session.refresh(user_server)

    assert changed == 1
    assert demo_server.status == "warning"
    assert user_server.status == "offline"
