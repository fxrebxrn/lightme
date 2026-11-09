"""Small text-formatting helpers shared by presenters."""

from __future__ import annotations

from datetime import date, datetime

from app.i18n import Texts

PLUG = '<tg-emoji emoji-id="6019346268197759615">🔌</tg-emoji>'
CALENDAR = '<tg-emoji emoji-id="5258105663359294787">🗓</tg-emoji>'
BOLT = '<tg-emoji emoji-id="6023761060786346622">⚡️</tg-emoji>'
RED = '<tg-emoji emoji-id="5330017696660599813">🔴</tg-emoji>'
GREEN = '<tg-emoji emoji-id="5330396907913098490">🟢</tg-emoji>'


def fmt_date(day: date) -> str:
    return day.strftime("%d.%m.%Y")


def fmt_number(value: float) -> str:
    """4.0 -> '4', 3.5 -> '3.5'."""
    value = round(value, 1)
    return str(int(value)) if float(value).is_integer() else str(value)


def hours_decimal(minutes: int) -> str:
    """Minutes -> hours with at most one decimal: 90 -> '1.5', 240 -> '4'."""
    hours = minutes / 60
    if hours.is_integer():
        return str(int(hours))
    return f"{hours:.1f}".rstrip("0").rstrip(".")


def remaining(minutes: int, t: Texts) -> str:
    """125 -> '2 год. 5 хв.'"""
    hours, mins = divmod(max(0, minutes), 60)
    parts = []
    if hours:
        parts.append(f"{hours} {t('units_hours')}")
    if mins:
        parts.append(f"{mins} {t('units_minutes')}")
    return " ".join(parts)


def event_duration(minutes: int, t: Texts) -> str:
    """Duration in timed notifications: '45 хв.' or '3.5 год.'"""
    minutes = max(0, minutes)
    if minutes < 60:
        return f"{minutes} {t('units_minutes')}"
    return f"{fmt_number(minutes / 60)} {t('units_hours')}"


def hours_minutes(minutes: int, t: Texts) -> str:
    """'3 год.' or '3 год. 30 хв.' (compare feature)."""
    hours, mins = divmod(minutes, 60)
    if mins == 0:
        return t("schedule_hours_value", value=hours)
    return f"{hours} {t('units_hours')} {mins} {t('units_minutes')}"


def updated_at(value: datetime, tz, t: Texts) -> str:
    local = value.astimezone(tz)
    return f"{local:%d.%m.%Y} {t('at')} {local:%H:%M:%S}"
