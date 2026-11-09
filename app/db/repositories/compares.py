from __future__ import annotations

from sqlalchemy import delete, func, select

from app.db.models import Compare
from app.db.repositories.base import Repository
from app.domain.enums import Company


class CompareRepository(Repository):
    async def list_for_user(self, user_id: int) -> list[Compare]:
        rows = await self.session.scalars(
            select(Compare).where(Compare.user_id == user_id).order_by(Compare.created_at.desc(), Compare.id.desc())
        )
        return list(rows)

    async def count_for_user(self, user_id: int) -> int:
        return int(await self.session.scalar(
            select(func.count()).select_from(Compare).where(Compare.user_id == user_id)
        ) or 0)

    async def get(self, compare_id: int, user_id: int) -> Compare | None:
        return await self.session.scalar(
            select(Compare).where(Compare.id == compare_id, Compare.user_id == user_id)
        )

    async def add(self, user_id: int, name: str, company1: Company, queue1: str,
                  company2: Company, queue2: str) -> Compare:
        item = Compare(user_id=user_id, name=name, company1=company1, queue1=queue1,
                       company2=company2, queue2=queue2)
        self.session.add(item)
        await self.session.flush()
        return item

    async def delete(self, compare_id: int, user_id: int) -> bool:
        result = await self.session.execute(
            delete(Compare).where(Compare.id == compare_id, Compare.user_id == user_id)
        )
        return result.rowcount > 0
