"""Unit of Work: one DB session + all repositories, one transaction per update."""

from __future__ import annotations

from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import SessionFactory
from app.db.repositories import (
    BotSettingsRepository,
    CompareRepository,
    ScheduleRepository,
    SubscriptionRepository,
    UserRepository,
)


class UnitOfWork:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._factory = session_factory
        self.session: AsyncSession | None = None

    async def __aenter__(self) -> UnitOfWork:
        self.session = self._factory()
        self.users = UserRepository(self.session)
        self.subscriptions = SubscriptionRepository(self.session)
        self.schedules = ScheduleRepository(self.session)
        self.compares = CompareRepository(self.session)
        self.bot_settings = BotSettingsRepository(self.session)
        return self

    async def __aexit__(self, exc_type: type[BaseException] | None, exc: BaseException | None,
                        tb: TracebackType | None) -> None:
        assert self.session is not None
        try:
            if exc_type is None:
                await self.session.commit()
            else:
                await self.session.rollback()
        finally:
            await self.session.close()

    async def commit(self) -> None:
        assert self.session is not None
        await self.session.commit()
