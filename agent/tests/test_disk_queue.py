"""Disk-backed payload queue tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from config import AgentConfig, QueueConfig
from models import CpuMetrics, MemoryMetrics, MetricPayload
from sender.disk_queue import DiskPayloadQueue, enqueue_and_flush, flush_queue
from sender.http_sender import ClientError


@pytest.fixture()
def sample_payload() -> MetricPayload:
    """Minimal metric payload for queue tests."""
    return MetricPayload(
        server_id="test-server",
        collected_at=datetime.now(tz=UTC),
        cpu=CpuMetrics(
            percent=25.0,
            per_core=[20.0, 30.0],
            load_avg_1=0.5,
            load_avg_5=0.4,
            load_avg_15=0.3,
        ),
        memory=MemoryMetrics(
            total_bytes=8_000_000_000,
            used_bytes=4_000_000_000,
            available_bytes=4_000_000_000,
            cached_bytes=1_000_000_000,
            percent=50.0,
            swap_total_bytes=2_000_000_000,
            swap_used_bytes=0,
        ),
        disks=[],
        networks=[],
        top_processes=[],
        services=[],
        log_entries=[],
    )


@pytest.fixture()
def queue_config(tmp_path: Path) -> AgentConfig:
    """Agent config with a temp queue directory."""
    return AgentConfig(
        server_id="test-server",
        backend_url="http://test-backend:8000",
        api_key="test-key",
        queue=QueueConfig(dir=str(tmp_path / "queue"), max_items=100, flush_batch_size=25),
    )


def test_enqueue_writes_payload_file(
    queue_config: AgentConfig,
    sample_payload: MetricPayload,
) -> None:
    """enqueue persists one JSON payload file."""
    queue = DiskPayloadQueue.from_config(queue_config)

    path = queue.enqueue(sample_payload)

    assert path.exists()
    assert len(queue.list_items()) == 1
    loaded = queue.load(path)
    assert loaded.server_id == sample_payload.server_id
    assert loaded.cpu.percent == sample_payload.cpu.percent


def test_enqueue_enforces_max_items(
    tmp_path: Path,
    sample_payload: MetricPayload,
) -> None:
    """Queue evicts oldest items when max_items is exceeded."""
    queue = DiskPayloadQueue(tmp_path / "queue", max_items=2)

    for _ in range(3):
        queue.enqueue(sample_payload)

    assert len(queue.list_items()) == 2


def test_flush_queue_removes_sent_items(
    monkeypatch: pytest.MonkeyPatch,
    queue_config: AgentConfig,
    sample_payload: MetricPayload,
) -> None:
    """Successful sends remove queued files."""
    queue = DiskPayloadQueue.from_config(queue_config)
    queue.enqueue(sample_payload)
    sent: list[MetricPayload] = []

    def fake_send(payload: MetricPayload, config: AgentConfig) -> bool:
        sent.append(payload)
        return True

    monkeypatch.setattr("sender.disk_queue.send_metrics", fake_send)

    assert flush_queue(queue_config, queue) is True
    assert len(sent) == 1
    assert queue.list_items() == []


def test_flush_queue_keeps_retryable_failure(
    monkeypatch: pytest.MonkeyPatch,
    queue_config: AgentConfig,
    sample_payload: MetricPayload,
) -> None:
    """Retryable send failure keeps the payload on disk."""
    queue = DiskPayloadQueue.from_config(queue_config)
    queue.enqueue(sample_payload)

    def fake_send(payload: MetricPayload, config: AgentConfig) -> bool:
        raise RuntimeError("network down")

    monkeypatch.setattr("sender.disk_queue.send_metrics", fake_send)

    assert flush_queue(queue_config, queue) is False
    assert len(queue.list_items()) == 1


def test_flush_queue_drops_client_error(
    monkeypatch: pytest.MonkeyPatch,
    queue_config: AgentConfig,
    sample_payload: MetricPayload,
) -> None:
    """Client errors are removed so a bad payload cannot block the queue."""
    queue = DiskPayloadQueue.from_config(queue_config)
    queue.enqueue(sample_payload)

    def fake_send(payload: MetricPayload, config: AgentConfig) -> bool:
        raise ClientError("HTTP 401")

    monkeypatch.setattr("sender.disk_queue.send_metrics", fake_send)

    assert flush_queue(queue_config, queue) is True
    assert queue.list_items() == []


def test_flush_queue_drops_corrupt_file(queue_config: AgentConfig) -> None:
    """Corrupt queue files are removed and do not block later items."""
    queue = DiskPayloadQueue.from_config(queue_config)
    queue.directory.mkdir(parents=True, exist_ok=True)
    (queue.directory / "0001-corrupt.json").write_text("{bad json", encoding="utf-8")

    assert flush_queue(queue_config, queue) is True
    assert queue.list_items() == []


def test_enqueue_and_flush_persists_before_send_failure(
    monkeypatch: pytest.MonkeyPatch,
    queue_config: AgentConfig,
    sample_payload: MetricPayload,
) -> None:
    """Current payload remains queued when immediate flush fails."""

    def fake_send(payload: MetricPayload, config: AgentConfig) -> bool:
        raise RuntimeError("network down")

    monkeypatch.setattr("sender.disk_queue.send_metrics", fake_send)

    assert enqueue_and_flush(sample_payload, queue_config) is False
    queue = DiskPayloadQueue.from_config(queue_config)
    assert len(queue.list_items()) == 1
