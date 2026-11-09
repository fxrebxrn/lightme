from __future__ import annotations

import time

from app.db.engine import SessionFactory
from app.db.uow import UnitOfWork
from app.domain.enums import BotFlag


class FlagsService:
    """Global switches (tech mode, emergency) with a small in-memory cache.

    The cache keeps the middleware from hitting the DB on every update; TTL
    keeps several bot replicas in sync.
    """

    def __init__(self, session_factory: SessionFactory, ttl: float = 5.0) -> None:
        self._factory = session_factory
        self._ttl = ttl
        self._cache: dict[BotFlag, bool] = {}
        self._loaded_at = 0.0

    async def is_enabled(self, flag: BotFlag) -> bool:
        if time.monotonic() - self._loaded_at > self._ttl:
            async with UnitOfWork(self._factory) as uow:
                self._cache = await uow.bot_settings.all()
            self._loaded_at = time.monotonic()
        return self._cache.get(flag, False)

    async def set(self, flag: BotFlag, enabled: bool) -> None:
        async with UnitOfWork(self._factory) as uow:
            await uow.bot_settings.set(flag, enabled)
        self._cache[flag] = enabled
        self._loaded_at = time.monotonic()
