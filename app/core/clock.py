from __future__ import annotations

from datetime import date, datetime, timedelta, tzinfo


class Clock:
    """Single source of 'now' in the bot timezone (easy to mock in tests)."""

    def __init__(self, tz: tzinfo) -> None:
        self.tz = tz

    def now(self) -> datetime:
        return datetime.now(self.tz)

    def today(self) -> date:
        return self.now().date()

    def tomorrow(self) -> date:
        return self.today() + timedelta(days=1)

    def localize(self, value: datetime) -> datetime:
        return value.astimezone(self.tz)
