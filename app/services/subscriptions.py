from __future__ import annotations

from enum import StrEnum

from app.db.models import Subscription
from app.db.uow import UnitOfWork
from app.domain.constants import QUEUES
from app.domain.enums import Company


class AddResult(StrEnum):
    ADDED = "added"
    EXISTS = "exists"
    LIMIT = "limit"
    INVALID = "invalid"


class SubscriptionService:
    def __init__(self, uow: UnitOfWork, max_subscriptions: int) -> None:
        self.uow = uow
        self.max_subscriptions = max_subscriptions

    async def list(self, user_id: int) -> list[Subscription]:
        return await self.uow.subscriptions.list_for_user(user_id)

    async def add(self, user_id: int, company: Company, queue: str) -> AddResult:
        if queue not in QUEUES:
            return AddResult.INVALID
        if await self.uow.subscriptions.exists(user_id, company, queue):
            return AddResult.EXISTS
        if await self.uow.subscriptions.count_for_user(user_id) >= self.max_subscriptions:
            return AddResult.LIMIT
        added = await self.uow.subscriptions.add(user_id, company, queue)
        return AddResult.ADDED if added else AddResult.EXISTS

    async def remove(self, user_id: int, subscription_id: int) -> bool:
        return await self.uow.subscriptions.delete(user_id, subscription_id)
