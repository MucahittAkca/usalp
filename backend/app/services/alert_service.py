"""Alert iş mantığı — listeleme, çözümleme, istatistik ve otomatik kurtarma."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import ColumnElement, case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.alert import Alert

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AlertFilters:
    """Alert listeleme filtre parametreleri."""

    server_id: int | None = None
    severity: str | None = None
    alert_type: str | None = None
    resolved: bool | None = None

    def to_where_clauses(self) -> list[ColumnElement]:
        clauses: list[ColumnElement] = []
        if self.server_id is not None:
            clauses.append(Alert.server_id == self.server_id)
        if self.severity is not None:
            clauses.append(Alert.severity == self.severity)
        if self.alert_type is not None:
            clauses.append(Alert.type == self.alert_type)
        if self.resolved is True:
            clauses.append(Alert.resolved_at.isnot(None))
        elif self.resolved is False:
            clauses.append(Alert.resolved_at.is_(None))
        return clauses


async def list_alerts(
    db: AsyncSession,
    filters: AlertFilters,
    *,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[Alert], int]:
    """Filtrelenmiş ve sayfalanmış alert listesi ile toplam sayıyı döndürür."""
    where = filters.to_where_clauses()

    total = await db.scalar(
        select(func.count(Alert.id)).where(*where)
    ) or 0

    stmt = (
        select(Alert)
        .where(*where)
        .order_by(Alert.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(stmt)
    alerts = list(result.scalars().all())

    return alerts, total


async def get_alert_or_404(db: AsyncSession, alert_id: int) -> Alert:
    """Alert'i ID ile bulur, yoksa NotFoundError fırlatır."""
    alert = await db.get(Alert, alert_id)
    if not alert:
        raise NotFoundError("Alert", alert_id)
    return alert


async def resolve_alert(db: AsyncSession, alert_id: int) -> Alert:
    """Alert'i çözüldü olarak işaretler. Zaten çözülmüşse tekrar güncellemez."""
    alert = await get_alert_or_404(db, alert_id)
    if alert.resolved_at is None:
        alert.resolved_at = datetime.now(UTC)
        await db.flush()
        logger.info("Alert çözüldü: id=%d type=%s", alert.id, alert.type)
    return alert


async def get_stats(
    db: AsyncSession, server_id: int | None = None,
) -> dict[str, int]:
    """Aktif alert istatistiklerini döndürür.

    Dönen sözlük: {total_active, critical, warning}
    """
    base_where: list[ColumnElement] = [Alert.resolved_at.is_(None)]
    if server_id is not None:
        base_where.append(Alert.server_id == server_id)

    stmt = select(
        func.count(Alert.id).label("total_active"),
        func.count(case((Alert.severity == "critical", Alert.id))).label("critical"),
        func.count(case((Alert.severity == "warning", Alert.id))).label("warning"),
    ).where(*base_where)

    row = (await db.execute(stmt)).one()

    return {
        "total_active": row.total_active,
        "critical": row.critical,
        "warning": row.warning,
    }


async def auto_resolve_by_type(
    db: AsyncSession, server_id: int, alert_type: str,
) -> int:
    """Belirtilen tipteki aktif alert'leri toplu çözümler.

    Metrik normale dönünce (ör. CPU < warning eşiği) çağrılır.
    Güncellenen satır sayısını döndürür.
    """
    stmt = (
        update(Alert)
        .where(
            Alert.server_id == server_id,
            Alert.type == alert_type,
            Alert.resolved_at.is_(None),
        )
        .values(resolved_at=datetime.now(UTC))
    )
    result = await db.execute(stmt)
    count = result.rowcount
    if count:
        logger.info(
            "Otomatik çözümleme: server=%d type=%s adet=%d",
            server_id, alert_type, count,
        )
    return count
