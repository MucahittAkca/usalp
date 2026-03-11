"""AI analiz şemaları."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

AISeverity = Literal["low", "medium", "high", "critical"]
AICategory = Literal[
    "network_error",
    "disk_issue",
    "permission_issue",
    "config_error",
    "dependency_failure",
    "resource_exhaustion",
    "unknown",
]


class CommandSuggestion(BaseModel):
    """AI tarafından önerilen tek bir komut."""

    command: str
    description: str


class AIAnalysisOut(BaseModel):
    """AI analiz yanıtı — causes ve commands yapısal olarak döndürülür."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    alert_id: int | None
    server_id: int
    category: str
    severity: str
    summary: str
    causes: list[str]
    commands: list[CommandSuggestion]
    confidence: float = Field(ge=0, le=1)
    created_at: datetime

    @field_validator("causes", mode="before")
    @classmethod
    def parse_causes(cls, v: str | list) -> list[str]:
        """ORM'den gelen JSON-encoded string'i listeye çevirir."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [v] if v else []
        return v

    @field_validator("commands", mode="before")
    @classmethod
    def parse_commands(cls, v: str | list) -> list[dict | CommandSuggestion]:
        """ORM'den gelen JSON-encoded string'i komut listesine çevirir."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return []
        return v


class AIAnalyzeRequest(BaseModel):
    """Manuel AI analiz tetikleme isteği."""

    model_config = ConfigDict(extra="forbid")

    server_id: int
    context: str | None = None
