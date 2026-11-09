from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert

from app.db.models import Subscription
from app.db.repositories.base import Repository
from app.domain.enums import Company


class SubscriptionRepository(Repository):
    async def list_for_user(self, user_id: int) -> list[Subscription]:
        rows = await self.session.scalars(
            select(Subscription).where(Subscription.user_id == user_id).order_by(Subscription.id)
        )
        return list(rows)

    async def count_for_user(self, user_id: int) -> int:
        return int(await self.session.scalar(
            select(func.count()).select_from(Subscription).where(Subscription.user_id == user_id)
        ) or 0)

    async def exists(self, user_id: int, company: Company, queue: str) -> bool:
        return bool(await self.session.scalar(
            select(Subscription.id).where(
                Subscription.user_id == user_id, Subscription.company == company, Subscription.queue == queue
            )
        ))

    async def add(self, user_id: int, company: Company, queue: str) -> bool:
        """Returns False if the subscription already existed."""
        result = await self.session.execute(
            insert(Subscription)
            .values(user_id=user_id, company=company, queue=queue)
            .on_conflict_do_nothing(index_elements=["user_id", "company", "queue"])
            .returning(Subscription.id)
        )
        return result.scalar() is not None

    async def delete(self, user_id: int, subscription_id: int) -> bool:
        result = await self.session.execute(
            delete(Subscription).where(Subscription.id == subscription_id, Subscription.user_id == user_id)
        )
        return result.rowcount > 0

    async def total(self) -> int:
        return int(await self.session.scalar(select(func.count()).select_from(Subscription)) or 0)
