from __future__ import annotations

from dataclasses import dataclass

from app.db.uow import UnitOfWork


@dataclass(frozen=True, slots=True)
class BotStats:
    users: int
    blocked: int
    subscriptions: int


async def collect_stats(uow: UnitOfWork) -> BotStats:
    users, blocked = await uow.users.counts()
    return BotStats(users=users, blocked=blocked, subscriptions=await uow.subscriptions.total())
