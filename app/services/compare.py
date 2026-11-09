from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from app.db.models import Compare
from app.db.uow import UnitOfWork
from app.domain.enums import Company
from app.domain.intervals import common_light, merge_intervals

Interval = tuple[int, int]


@dataclass(frozen=True, slots=True)
class QueueRef:
    company: Company
    queue: str

    @property
    def title(self) -> str:
        return f"{self.company.title} {self.queue}"


@dataclass(frozen=True, slots=True)
class CompareResult:
    first: QueueRef
    second: QueueRef
    day: date
    has_data: bool
    offs1: tuple[Interval, ...] = ()
    offs2: tuple[Interval, ...] = ()
    common: tuple[Interval, ...] = ()


class SaveResult(StrEnum):
    SAVED = "saved"
    LIMIT = "limit"


class CompareService:
    def __init__(self, uow: UnitOfWork, max_compares: int) -> None:
        self.uow = uow
        self.max_compares = max_compares

    async def compare(self, first: QueueRef, second: QueueRef, day: date) -> CompareResult:
        s1 = await self.uow.schedules.get(first.company, first.queue, day)
        s2 = await self.uow.schedules.get(second.company, second.queue, day)
        if s1 is None or s2 is None:
            return CompareResult(first, second, day, has_data=False)
        offs1 = tuple(merge_intervals(s1.intervals))
        offs2 = tuple(merge_intervals(s2.intervals))
        return CompareResult(
            first, second, day, has_data=True, offs1=offs1, offs2=offs2,
            common=tuple(common_light(offs1, offs2)),
        )

    async def save(self, user_id: int, first: QueueRef, second: QueueRef) -> tuple[SaveResult, str]:
        name = f"{first.title} + {second.title}"
        if await self.uow.compares.count_for_user(user_id) >= self.max_compares:
            return SaveResult.LIMIT, name
        await self.uow.compares.add(user_id, name, first.company, first.queue, second.company, second.queue)
        return SaveResult.SAVED, name

    async def list(self, user_id: int) -> list[Compare]:
        return await self.uow.compares.list_for_user(user_id)

    async def get(self, user_id: int, compare_id: int) -> Compare | None:
        return await self.uow.compares.get(compare_id, user_id)

    async def delete(self, user_id: int, compare_id: int) -> bool:
        return await self.uow.compares.delete(compare_id, user_id)
