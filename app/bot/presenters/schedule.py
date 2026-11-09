"""Texts for schedules: schedule card, update notification, inline result."""

from __future__ import annotations

from datetime import date, datetime

from app.bot.presenters.formatting import (
    CALENDAR,
    PLUG,
    fmt_date,
    fmt_number,
    hours_decimal,
    remaining,
    updated_at,
)
from app.domain.constants import MINUTES_IN_DAY
from app.domain.enums import Company
from app.domain.intervals import merge_intervals, total_minutes
from app.domain.timeutils import fmt_minute
from app.i18n import Texts
from app.services.schedules import QueueDay

Interval = tuple[int, int]


def status_line(outages: tuple[Interval, ...], now: datetime, t: Texts) -> str:
    now_minute = now.hour * 60 + now.minute
    for start, end in outages:
        if start <= now_minute < end:
            return t("status_no_light_until", time=fmt_minute(end), remain=remaining(end - now_minute, t))
    for start, _ in outages:
        if now_minute < start:
            return t("status_light_until", time=fmt_minute(start), remain=remaining(start - now_minute, t))
    return t("status_light_now")


def schedule_card(view: QueueDay, *, now: datetime, emergency: bool, t: Texts) -> str:
    title = f"{CALENDAR} " + t("schedule_title", company=view.company.title, queue=view.queue, date=fmt_date(view.day))
    avar = f"\n\n{t('avar_warning')}" if emergency else ""
    footer = f"{t('monitor_link')}\n"

    if not view.loaded:
        return f"{title}\n\n{t('schedule_not_loaded')}{avar}\n\n{footer}"

    updated = f"<i>{t('updated')} {updated_at(view.updated_at, now.tzinfo, t)}</i>" if view.updated_at else ""
    if not view.has_outages:
        return f"{title}\n\n{t('no_outages_today')}{avar}\n\n{updated}\n\n{footer}"

    lines = [
        f"{PLUG} {fmt_minute(s)} - {fmt_minute(e)} <i>({t('schedule_hours_value', value=hours_decimal(e - s))})</i>"
        for s, e in view.outages
    ]
    off_minutes = total_minutes(merge_intervals(view.outages))
    on_minutes = max(0, MINUTES_IN_DAY - off_minutes)
    status = f"{status_line(view.outages, now, t)}\n\n" if view.day == now.date() else ""
    return (
        f"{title}\n\n"
        f"{status}"
        f"{t('section_outages')}\n" + "\n".join(lines) + "\n\n"
        f"{t('section_stats')}\n"
        f"{t('stats_light', value=t('schedule_hours_value', value=hours_decimal(on_minutes)))}\n"
        f"{t('stats_no_light', value=t('schedule_hours_value', value=hours_decimal(off_minutes)))}{avar}\n\n"
        f"{updated}\n\n"
        f"{footer}"
    )


def update_notification(company: Company, queue: str, day: date, outages: tuple[Interval, ...], t: Texts) -> str:
    """Sent to subscribers when admin uploads a changed schedule."""
    header = t("update_notify", company=company.title, queue=queue, date=fmt_date(day))
    footer = t("monitor_link")
    if not outages:
        return f"{header}\n\n<b>{t('no_outages')}</b>\n\n{footer}"

    unit = t("hour_short_dot")
    lines = [f"{PLUG} {fmt_minute(s)} - {fmt_minute(e)} ({fmt_number((e - s) / 60)} {unit})" for s, e in outages]
    off_h = round(total_minutes(outages) / 60, 1)
    on_h = round(24 - off_h, 1)
    return (
        f"{header}\n\n"
        f"{t('notify_outages_title')}\n" + "\n".join(lines) + "\n\n"
        f"{t('notify_stats_title')}\n"
        f"{t('notify_on_label')} {fmt_number(on_h)} {unit}\n"
        f"{t('notify_off_label')} {fmt_number(off_h)} {unit}"
        f"\n\n{footer}"
    )


def _half_hours(minutes: int) -> str:
    return fmt_number(round((minutes / 60) * 2) / 2)


def inline_schedule(view: QueueDay, t: Texts) -> str:
    """Text of the inline-mode result (@bot ДТЕК 1.1 завтра)."""
    if not view.loaded:
        body = "\n" + t("inline_not_loaded")
    elif not view.has_outages:
        body = "\n" + t("inline_no_outages")
    else:
        lines = []
        total = 0
        for s, e in view.outages:
            total += e - s
            lines.append(f"🔌 {fmt_minute(s)} - {fmt_minute(e)} <i>({_half_hours(e - s)} {t('inline_hours')})</i>")
        off_h = round((total / 60) * 2) / 2
        body = (
            "\n" + "\n".join(lines) + "\n\n"
            + t("inline_with_light", value=fmt_number(24 - off_h)) + "\n"
            + t("inline_without_light", value=fmt_number(off_h))
        )
    header = t("inline_header", company=view.company.title, queue=view.queue, date=fmt_date(view.day))
    return f"{header}\n{body}\n\n{t('inline_footer')}"
