from __future__ import annotations

from collections import defaultdict
from typing import Any, AsyncIterator
import asyncio


class EventBus:
    def __init__(self) -> None:
        self._queues: dict[str, set[asyncio.Queue[dict[str, Any]]]] = defaultdict(set)

    async def publish(self, topic: str, event: dict[str, Any]) -> None:
        for queue in tuple(self._queues.get(topic, ())):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                try:
                    queue.get_nowait()
                    queue.put_nowait(event)
                except (asyncio.QueueEmpty, asyncio.QueueFull):
                    pass

    async def subscribe(self, topic: str) -> AsyncIterator[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=256)
        self._queues[topic].add(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            self._queues[topic].discard(queue)
