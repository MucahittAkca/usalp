"""Canlı metrik yayını için in-process pub/sub hub."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import Final

from app.schemas.metric import MetricOut

QUEUE_SIZE: Final = 100


class MetricStreamHub:
    """SSE istemcilerine yeni metrik kayıtlarını dağıtır."""

    def __init__(self) -> None:
        self._subscribers: dict[int, set[asyncio.Queue[MetricOut]]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, server_id: int) -> asyncio.Queue[MetricOut]:
        """Bir sunucu için yeni abonelik kuyruğu oluşturur."""
        queue: asyncio.Queue[MetricOut] = asyncio.Queue(maxsize=QUEUE_SIZE)
        async with self._lock:
            self._subscribers.setdefault(server_id, set()).add(queue)
        return queue

    async def unsubscribe(self, server_id: int, queue: asyncio.Queue[MetricOut]) -> None:
        """Abonelik kuyruğunu kaldırır."""
        async with self._lock:
            subscribers = self._subscribers.get(server_id)
            if not subscribers:
                return
            subscribers.discard(queue)
            if not subscribers:
                self._subscribers.pop(server_id, None)

    async def publish(self, server_id: int, metric: MetricOut) -> None:
        """Yeni metriği bağlı istemcilere non-blocking olarak yollar."""
        async with self._lock:
            queues = list(self._subscribers.get(server_id, set()))

        for queue in queues:
            if queue.full():
                with suppress(asyncio.QueueEmpty):
                    queue.get_nowait()
            queue.put_nowait(metric)


hub = MetricStreamHub()
