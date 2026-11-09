"""Pure planner of timed notifications.

Takes the uploaded schedules and returns the list of events that must be sent
(switch off / switch on / reminders). It knows nothing about Telegram or DB,
so it is easy to test and to reuse.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, tzinfo

from app.domain.enums import Company, EventKind
from app.domain.timeutils import END_OF_DAY, is_end_of_day

Interval = tuple[int, int]

ScheduleIndex = Mapping[tuple[Company, str], Mapping[date, Sequence[Interval]]]

_CHAIN_DAYS_LIMIT = 7


@dataclass(frozen=True, slots=True)
class PlannedEvent:
    company: Company
    queue: str
    kind: EventKind
    run_at: datetime
    event_at: datetime
    next_at: datetime | None

    @property
    def job_id(self) -> str:
        return f"{self.company}:{self.queue}:{self.kind}:{self.run_at.isoformat()}"


def to_datetime(day: date, minute: int, tz: tzinfo) -> datetime:
    """(2026-01-29, 1440) -> 2026-01-30 00:00 local time."""
    extra_days, minute = divmod(minute, END_OF_DAY)
    local = datetime.combine(day + timedelta(days=extra_days), time(minute // 60, minute % 60))
    return local.replace(tzinfo=tz)


class NotificationPlanner:
    def __init__(self, tz: tzinfo, reminder_minutes: int = 10) -> None:
        self.tz = tz
        self.reminder = timedelta(minutes=reminder_minutes)

    def plan(self, index: ScheduleIndex, now: datetime) -> list[PlannedEvent]:
        events: list[PlannedEvent] = []
        for (company, queue), days in index.items():
            for day in days:
                events.extend(self._plan_day(company, queue, day, days, now))
        unique = {e.job_id: e for e in events}
        return sorted(unique.values(), key=lambda e: e.run_at)


    def _plan_day(self, company, queue, day, days, now) -> list[PlannedEvent]:
        result: list[PlannedEvent] = []
        intervals = sorted(days.get(day, ()))
        prev_day = days.get(day - timedelta(days=1), ())
        next_day = days.get(day + timedelta(days=1), ())

        for start, end in intervals:
            off_at = to_datetime(day, start, self.tz)
            on_at = to_datetime(day, end, self.tz)


            continues_from_prev = start == 0 and any(is_end_of_day(e) for _, e in prev_day)

            continues_to_next = is_end_of_day(end) and any(s == 0 for s, _ in next_day)

            if not continues_from_prev:
                self._add(result, company, queue, EventKind.OFF_REMINDER, off_at - self.reminder, off_at, None, now)
                self._add(
                    result, company, queue, EventKind.OFF_NOW, off_at, off_at,
                    self._effective_on(day, end, days), now,
                )
            if not continues_to_next:
                self._add(result, company, queue, EventKind.ON_REMINDER, on_at - self.reminder, on_at, None, now)
                self._add(
                    result, company, queue, EventKind.ON_NOW, on_at, on_at,
                    self._next_off(day, end, days), now,
                )
        return result

    @staticmethod
    def _add(result, company, queue, kind, run_at, event_at, next_at, now) -> None:
        if run_at > now:
            result.append(PlannedEvent(company, queue, kind, run_at, event_at, next_at))

    def _effective_on(self, day: date, end: int, days) -> datetime:
        """When the light really comes back (outage may continue on next days)."""
        cur_day, cur_end = day, end
        for _ in range(_CHAIN_DAYS_LIMIT):
            if not is_end_of_day(cur_end):
                break
            following = [e for s, e in days.get(cur_day + timedelta(days=1), ()) if s == 0]
            if not following:
                break
            cur_day, cur_end = cur_day + timedelta(days=1), min(following)
        return to_datetime(cur_day, cur_end, self.tz)

    def _next_off(self, day: date, end: int, days) -> datetime | None:
        same_day = [s for s, _ in days.get(day, ()) if s > end]
        if same_day:
            return to_datetime(day, min(same_day), self.tz)
        next_day = [s for s, _ in days.get(day + timedelta(days=1), ())]
        if next_day:
            return to_datetime(day + timedelta(days=1), min(next_day), self.tz)
        return None
