"""Ortak test fixture'ları."""

from __future__ import annotations

import pytest

from agent.config import AgentConfig, LogFileConfig


@pytest.fixture()
def agent_config() -> AgentConfig:
    """Testlerde kullanılacak minimal ``AgentConfig`` örneği."""
    return AgentConfig(
        server_id="test-server-01",
        backend_url="http://localhost:8000",
        api_key="test-api-key",
        services=["nginx", "docker"],
        log_files=[
            LogFileConfig(path="/var/log/syslog", tail_lines=50, min_level="WARNING"),
        ],
    )
