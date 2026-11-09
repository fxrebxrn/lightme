"""Helpers for 'minute of day' arithmetic.

Schedules are stored as integer minutes from midnight:
    start_minute: 0..1439
    end_minute:   1..1440   (1440 == end of day, typed by admins as 00:00 or 24:00)
"""

from __future__ import annotations

import re

from app.domain.constants import MINUTES_IN_DAY

END_OF_DAY = MINUTES_IN_DAY
_TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})$")


def parse_hhmm(value: str) -> int:
    """'07:30' -> 450, '24:00' -> 1440. Raises ValueError on bad input."""
    match = _TIME_RE.match(value.strip())
    if not match:
        raise ValueError(f"Bad time: {value!r}")
    hours, minutes = int(match.group(1)), int(match.group(2))
    if minutes > 59 or hours > 24 or (hours == 24 and minutes != 0):
        raise ValueError(f"Bad time: {value!r}")
    return hours * 60 + minutes


def normalize_interval(start: int, end: int) -> tuple[int, int]:
    """End 00:00 (or any end <= start) means 'until the end of the day'."""
    if end <= start:
        end = END_OF_DAY
    return start, end


def fmt_minute(minute: int, *, end_of_day: str = "00:00") -> str:
    """Formats minute of day as HH:MM. 1440 is rendered as `end_of_day`."""
    if minute >= MINUTES_IN_DAY:
        if minute == MINUTES_IN_DAY:
            return end_of_day
        minute %= MINUTES_IN_DAY
    return f"{minute // 60:02d}:{minute % 60:02d}"


def is_end_of_day(minute: int) -> bool:
    """23:59 and 24:00 both mean the outage lasts until midnight."""
    return minute >= END_OF_DAY - 1
