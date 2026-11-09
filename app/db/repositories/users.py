from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert

from app.db.models import Subscription, User
from app.db.repositories.base import Repository
from app.domain.enums import Company


class UserRepository(Repository):
    async def get(self, user_id: int) -> User | None:
        return await self.session.get(User, user_id)

    async def upsert(self, user_id: int, *, username: str | None, full_name: str | None,
                     default_language: str) -> User:
        """Creates the user on first contact; refreshes name and re-activates on next ones."""
        user = await self.session.get(User, user_id)
        if user is None:
            await self.session.execute(
                insert(User)
                .values(id=user_id, username=username, full_name=full_name, language=default_language)
                .on_conflict_do_nothing(index_elements=[User.id])
            )
            user = await self.session.get(User, user_id)
            assert user is not None
            return user
        if user.username != username:
            user.username = username
        if user.full_name != full_name:
            user.full_name = full_name
        if not user.is_active:
            user.is_active = True
        return user

    async def set_fields(self, user_id: int, **values) -> None:
        await self.session.execute(update(User).where(User.id == user_id).values(**values))

    async def deactivate(self, user_ids: Sequence[int]) -> None:
        if user_ids:
            await self.session.execute(
                update(User).where(User.id.in_(user_ids)).values(is_active=False)
            )

    async def active_ids(self) -> list[int]:
        rows = await self.session.scalars(select(User.id).where(User.is_active.is_(True)).order_by(User.id))
        return list(rows)

    async def recipients(self, company: Company, queue: str, pref_field: str | None = None) -> list[tuple[int, str]]:
        """(user_id, language) of active users subscribed to the queue."""
        stmt = (
            select(User.id, User.language)
            .join(Subscription, Subscription.user_id == User.id)
            .where(Subscription.company == company, Subscription.queue == queue, User.is_active.is_(True))
        )
        if pref_field:
            stmt = stmt.where(getattr(User, pref_field).is_(True))
        return [(r.id, r.language) for r in await self.session.execute(stmt)]

    async def counts(self) -> tuple[int, int]:
        """(all users, users that blocked the bot)."""
        total = await self.session.scalar(select(func.count()).select_from(User))
        blocked = await self.session.scalar(select(func.count()).select_from(User).where(User.is_active.is_(False)))
        return int(total or 0), int(blocked or 0)
