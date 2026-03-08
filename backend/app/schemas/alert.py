"""Alert şemaları."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AlertOut(BaseModel):
    """Alert yanıtı."""

    id: int
    server_id: int
    type: str
    severity: str
    message: str
    resolved_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
