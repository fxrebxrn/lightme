from __future__ import annotations

import asyncio
import logging
from collections.abc import Coroutine

log = logging.getLogger(__name__)


class BackgroundTasks:
    """Keeps references to fire-and-forget tasks and logs their errors."""

    def __init__(self) -> None:
        self._tasks: set[asyncio.Task] = set()

    def spawn(self, coro: Coroutine) -> asyncio.Task:
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._done)
        return task

    def _done(self, task: asyncio.Task) -> None:
        self._tasks.discard(task)
        if not task.cancelled() and task.exception():
            log.error("Background task failed", exc_info=task.exception())

    async def wait(self, timeout: float = 10) -> None:
        if self._tasks:
            await asyncio.wait(self._tasks, timeout=timeout)
