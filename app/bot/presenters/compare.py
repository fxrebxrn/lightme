"""Texts of the 'common light' (спільне світло) feature."""

from __future__ import annotations

from app.bot.presenters.formatting import BOLT, PLUG, fmt_date, hours_minutes
from app.domain.timeutils import fmt_minute
from app.i18n import Texts
from app.services.compare import CompareResult

Interval = tuple[int, int]


def _span(s: int, e: int, t: Texts, icon: str) -> str:
    start, end = fmt_minute(s, end_of_day="24:00"), fmt_minute(e, end_of_day="24:00")
    return f"{icon} {start} - {end} <i>({hours_minutes(e - s, t)})</i>"


def _names(result: CompareResult) -> dict:
    return dict(
        comp1=result.first.company.title, queue1=result.first.queue,
        comp2=result.second.company.title, queue2=result.second.queue,
        date=fmt_date(result.day),
    )


def no_data(result: CompareResult, t: Texts) -> str:
    return t("cmp_no_data", **_names(result))


def no_common(result: CompareResult, t: Texts) -> str:
    return t("cmp_no_common", **_names(result))


def common_light(result: CompareResult, t: Texts) -> str:
    lines = [_span(s, e, t, BOLT) for s, e in result.common]
    return f"{t('cmp_result_header', **_names(result))}\n\n" + "\n".join(lines) + f"\n\n{t('monitor_link')}"


def _outages(offs: tuple[Interval, ...], t: Texts) -> str:
    lines = [_span(s, e, t, PLUG) for s, e in offs if e - s > 0 and not (s == 1439 and e == 1440)]
    return "\n".join(lines) if lines else t("no_outages")


def details(result: CompareResult, t: Texts) -> str:
    return (
        f"{t('cmp_details_header', **_names(result))}\n\n"
        f"{t('cmp_original_1', comp=result.first.company.title, queue=result.first.queue)}\n"
        f"{_outages(result.offs1, t)}\n\n"
        f"{t('cmp_original_2', comp=result.second.company.title, queue=result.second.queue)}\n"
        f"{_outages(result.offs2, t)}\n\n"
        f"{t('monitor_link')}"
    )
