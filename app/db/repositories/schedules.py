from __future__ import annotations

from collections.abc import Iterable
from datetime import date

from sqlalchemy import delete, func, select

from app.db.models import Outage, QueueSchedule
from app.db.repositories.base import Repository
from app.domain.enums import Company


class ScheduleRepository(Repository):
    async def get(self, company: Company, queue: str, day: date) -> QueueSchedule | None:
        return await self.session.scalar(
            select(QueueSchedule).where(
                QueueSchedule.company == company, QueueSchedule.queue == queue, QueueSchedule.day == day
            )
        )

    async def for_company_day(self, company: Company, day: date) -> dict[str, QueueSchedule]:
        rows = await self.session.scalars(
            select(QueueSchedule).where(QueueSchedule.company == company, QueueSchedule.day == day)
        )
        return {row.queue: row for row in rows}

    async def since(self, first_day: date) -> list[QueueSchedule]:
        rows = await self.session.scalars(
            select(QueueSchedule).where(QueueSchedule.day >= first_day).order_by(QueueSchedule.day)
        )
        return list(rows)

    async def replace_queue(self, company: Company, queue: str, day: date,
                            intervals: Iterable[tuple[int, int]]) -> QueueSchedule:
        """Creates/overwrites one queue schedule and bumps `updated_at`."""
        item = await self.get(company, queue, day)
        if item is None:
            item = QueueSchedule(company=company, queue=queue, day=day)
            self.session.add(item)
        item.updated_at = func.now()
        item.outages = [Outage(start_minute=s, end_minute=e) for s, e in intervals]
        await self.session.flush()
        await self.session.refresh(item, ["updated_at"])
        return item

    async def delete_queues(self, company: Company, day: date, queues: Iterable[str]) -> None:
        queues = list(queues)
        if queues:
            await self.session.execute(
                delete(QueueSchedule).where(
                    QueueSchedule.company == company, QueueSchedule.day == day, QueueSchedule.queue.in_(queues)
                )
            )
