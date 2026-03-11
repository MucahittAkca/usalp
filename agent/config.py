"""Agent yapılandırma modülü.

``agent.yaml`` dosyasını okuyarak Pydantic modeline dönüştürür.
Tüm diğer modüller yapılandırma bilgisini bu modelden alır.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel


class IntervalsConfig(BaseModel):
    """Fast/slow toplama döngüsü aralıkları (saniye)."""

    fast: int = 30
    slow: int = 60


class LogFileConfig(BaseModel):
    """Tek bir log dosyasının okuma yapılandırması."""

    path: str
    tail_lines: int = 100
    min_level: str = "ERROR"


class AgentConfig(BaseModel):
    """Agent'ın tüm çalışma parametrelerini tutan kök model."""

    server_id: str
    backend_url: str
    api_key: str
    intervals: IntervalsConfig = IntervalsConfig()
    services: list[str] = []
    log_files: list[LogFileConfig] = []


def load_config(path: Path | str = "agent.yaml") -> AgentConfig:
    """YAML dosyasını okuyarak ``AgentConfig`` döndürür."""
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    return AgentConfig(**raw)
