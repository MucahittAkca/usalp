"""AI analiz şemaları."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AIAnalysisOut(BaseModel):
    """AI analiz yanıtı."""

    id: int
    alert_id: int | None
    server_id: int
    category: str
    severity: str
    summary: str
    causes: str
    commands: str
    confidence: float
    created_at: datetime

    model_config = {"from_attributes": True}


class AIAnalyzeRequest(BaseModel):
    """Manuel AI analiz tetikleme isteği."""

    server_id: int
    context: str | None = None
