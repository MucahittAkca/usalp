"""Alert şemaları."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

Severity = Literal["warning", "critical"]


class AlertOut(BaseModel):
    """Alert yanıtı."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    server_id: int
    type: str
    severity: str
    message: str
    resolved_at: datetime | None
    created_at: datetime
