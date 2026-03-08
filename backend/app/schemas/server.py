"""Server şemaları."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ServerOut(BaseModel):
    """Sunucu listesi ve detay yanıtı."""

    id: int
    name: str
    hostname: str
    ip_address: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
