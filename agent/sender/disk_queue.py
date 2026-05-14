"""Local disk queue for metric payloads."""

from __future__ import annotations

import os
import time
from pathlib import Path
from uuid import uuid4

import structlog

from config import AgentConfig
from models import MetricPayload
from sender.http_sender import ClientError, send_metrics

log = structlog.get_logger()


class PayloadQueueCorruptError(Exception):
    """Stored queue item cannot be parsed as a metric payload."""


class DiskPayloadQueue:
    """File-backed FIFO queue for metric payloads."""

    def __init__(self, directory: Path, *, max_items: int = 1000) -> None:
        self.directory = directory
        self.max_items = max_items

    @classmethod
    def from_config(cls, config: AgentConfig) -> DiskPayloadQueue:
        """Build a queue from agent config."""
        return cls(Path(config.queue.dir), max_items=config.queue.max_items)

    def enqueue(self, payload: MetricPayload) -> Path:
        """Persist a payload atomically and return the queue file path."""
        self.directory.mkdir(parents=True, exist_ok=True)
        filename = f"{time.time_ns()}-{uuid4().hex}.json"
        target = self.directory / filename
        tmp = self.directory / f".{filename}.tmp"

        tmp.write_text(payload.model_dump_json(), encoding="utf-8")
        os.replace(tmp, target)
        self._enforce_limit()
        log.info("payload_queued", path=str(target))
        return target

    def list_items(self) -> list[Path]:
        """Return queue item files in FIFO order."""
        if not self.directory.exists():
            return []
        return sorted(path for path in self.directory.glob("*.json") if path.is_file())

    def load(self, path: Path) -> MetricPayload:
        """Load a queue item from disk."""
        try:
            return MetricPayload.model_validate_json(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise PayloadQueueCorruptError(str(path)) from exc

    def remove(self, path: Path) -> None:
        """Remove a queue item if it still exists."""
        path.unlink(missing_ok=True)

    def _enforce_limit(self) -> None:
        """Keep queue size bounded by dropping oldest items when necessary."""
        if self.max_items <= 0:
            return

        items = self.list_items()
        overflow = len(items) - self.max_items
        if overflow <= 0:
            return

        for path in items[:overflow]:
            self.remove(path)
            log.warning("payload_queue_evicted", path=str(path), max_items=self.max_items)


def flush_queue(config: AgentConfig, queue: DiskPayloadQueue | None = None) -> bool:
    """Send queued payloads in FIFO order.

    Returns ``True`` when the queue is empty or fully flushed. Retryable failures
    keep the current item on disk and stop the flush; client errors and corrupt
    files are removed so one bad item cannot block newer data forever.
    """
    queue = queue or DiskPayloadQueue.from_config(config)
    sent = 0

    for path in queue.list_items()[: config.queue.flush_batch_size]:
        try:
            payload = queue.load(path)
        except PayloadQueueCorruptError:
            log.exception("payload_queue_corrupt", path=str(path))
            queue.remove(path)
            continue

        try:
            send_metrics(payload, config)
        except ClientError:
            log.error("payload_queue_dropped_client_error", path=str(path))
            queue.remove(path)
            continue
        except Exception:
            log.exception("payload_queue_flush_failed", path=str(path))
            return False

        queue.remove(path)
        sent += 1
        log.info("payload_queue_sent", path=str(path))

    remaining = len(queue.list_items())
    if sent:
        log.info("payload_queue_flush_done", sent=sent, remaining=remaining)
    return remaining == 0


def enqueue_and_flush(payload: MetricPayload, config: AgentConfig) -> bool:
    """Persist payload first, then try to flush the queue."""
    queue = DiskPayloadQueue.from_config(config)
    queue.enqueue(payload)
    return flush_queue(config, queue)
