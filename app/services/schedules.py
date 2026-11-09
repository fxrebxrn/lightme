from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from app.db.uow import UnitOfWork
from app.domain.enums import Company
from app.domain.planner import ScheduleIndex
from app.domain.schedule import DaySchedule

Interval = tuple[int, int]


@dataclass(frozen=True, slots=True)
class QueueDay:
    """Read model of one queue schedule for one day."""

    company: Company
    queue: str
    day: date
    loaded: bool
    outages: tuple[Interval, ...] = ()
    updated_at: datetime | None = None

    @property
    def has_outages(self) -> bool:
        return bool(self.outages)


@dataclass(slots=True)
class UploadResult:
    company: Company
    day: date
    schedule: DaySchedule
    changed: set[str] = field(default_factory=set)
    had_previous: bool = False
    saved: bool = False

    @property
    def unchanged(self) -> bool:
        return not self.saved


class ScheduleService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def get_day(self, company: Company, queue: str, day: date) -> QueueDay:
        item = await self.uow.schedules.get(company, queue, day)
        if item is None:
            return QueueDay(company, queue, day, loaded=False)
        return QueueDay(company, queue, day, loaded=True, outages=item.intervals, updated_at=item.updated_at)

    async def apply_upload(self, schedule: DaySchedule, *, force: bool = False) -> UploadResult:
        """Replaces the schedule of a company for a day.

        Queues missing in the upload are removed (the upload is the full schedule
        for the day). Only queues whose intervals changed are reported in
        `changed` (these get an update notification).
        """
        result = UploadResult(company=schedule.company, day=schedule.day, schedule=schedule)
        current = await self.uow.schedules.for_company_day(schedule.company, schedule.day)
        result.had_previous = bool(current)

        for queue, new in schedule.queues.items():
            old = current.get(queue)
            if old is None or tuple(old.intervals) != tuple(new.outages):
                result.changed.add(queue)

        if not result.changed and result.had_previous and not force:
            return result

        removed = set(current) - set(schedule.queues)
        await self.uow.schedules.delete_queues(schedule.company, schedule.day, removed)
        for queue in sorted(result.changed):
            await self.uow.schedules.replace_queue(
                schedule.company, queue, schedule.day, schedule.queues[queue].outages
            )
        result.saved = True
        return result

    async def build_index(self, today: date) -> ScheduleIndex:
        """Schedules from yesterday on, grouped for the notification planner."""
        index: dict[tuple[Company, str], dict[date, tuple[Interval, ...]]] = defaultdict(dict)
        for item in await self.uow.schedules.since(today - timedelta(days=1)):
            index[(item.company, item.queue)][item.day] = item.intervals
        return index
