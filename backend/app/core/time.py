"""Datetime normalizasyon yardımcıları."""

from __future__ import annotations

from datetime import UTC, datetime


def utc_now_naive() -> datetime:
    """TIMESTAMP WITHOUT TIME ZONE kolonları için naive UTC zaman üretir."""
    return datetime.now(UTC).replace(tzinfo=None)


def as_naive_utc(value: datetime) -> datetime:
    """Datetime değerini timezone'suz UTC'ye çevirir.

    PostgreSQL TIMESTAMP WITHOUT TIME ZONE kolonlarına asyncpg ile timezone-aware
    datetime gönderildiğinde encode hatası oluşur.
    """
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)
