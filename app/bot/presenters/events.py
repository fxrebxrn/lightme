"""Texts of timed notifications (switch off/on + reminders)."""

from __future__ import annotations

from datetime import datetime

from app.bot.presenters.formatting import event_duration
from app.domain.enums import Company, EventKind
from app.i18n import Texts


def event_text(kind: EventKind, company: Company, queue: str, event_at: datetime,
               next_at: datetime | None, reminder_minutes: int, t: Texts) -> str:
    if kind is EventKind.OFF_REMINDER:
        return t("reminder_off", company=company.title, queue=queue, minutes=reminder_minutes)
    if kind is EventKind.ON_REMINDER:
        return t("reminder_on", company=company.title, queue=queue, minutes=reminder_minutes)

    key = "off_now_extended" if kind is EventKind.OFF_NOW else "on_now_extended"
    if next_at is not None:
        next_time = f"{next_at:%H:%M}"
        duration = event_duration(int((next_at - event_at).total_seconds() // 60), t)
    else:
        next_time = duration = "??"
    return t(key, company=company.title, queue=queue, time=f"{event_at:%H:%M}",
             next_time=next_time, duration=duration)
