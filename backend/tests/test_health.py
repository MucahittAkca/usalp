"""Health endpoint testi."""

from __future__ import annotations

import io
import tarfile
from pathlib import Path

import pytest
from httpx import AsyncClient

from app import main as main_module


@pytest.mark.asyncio
async def test_health_returns_ok(client: AsyncClient) -> None:
    """Health endpoint 200 döner ve DB bağlantısı başarılıdır."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["database"] == "connected"


@pytest.mark.asyncio
async def test_agent_tarball_uses_runtime_allowlist(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Agent paketi test/cache/sample config dosyalarını içermez."""
    agent_dir = tmp_path / "agent"
    (agent_dir / "collectors").mkdir(parents=True)
    (agent_dir / "tests").mkdir()
    (agent_dir / "__pycache__").mkdir()
    (agent_dir / "main.py").write_text("print('ok')\n", encoding="utf-8")
    (agent_dir / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (agent_dir / "agent.yaml").write_text("api_key: secret\n", encoding="utf-8")
    (agent_dir / "collectors" / "cpu.py").write_text("x=1\n", encoding="utf-8")
    (agent_dir / "tests" / "test_agent.py").write_text("x=1\n", encoding="utf-8")
    (agent_dir / "__pycache__" / "main.pyc").write_bytes(b"pyc")

    monkeypatch.setattr(main_module, "AGENT_SOURCE_DIR", agent_dir)

    resp = await client.get("/agent.tar.gz")

    assert resp.status_code == 200
    with tarfile.open(fileobj=io.BytesIO(resp.content), mode="r:gz") as tar:
        names = set(tar.getnames())

    assert "usalp-agent/main.py" in names
    assert "usalp-agent/pyproject.toml" in names
    assert "usalp-agent/collectors/cpu.py" in names
    assert "usalp-agent/agent.yaml" not in names
    assert all("/tests/" not in name and "__pycache__" not in name for name in names)
