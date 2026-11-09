"""Schedule domain model + parser of admin text (/upload)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime

from app.domain.constants import QUEUES
from app.domain.enums import Company
from app.domain.timeutils import normalize_interval, parse_hhmm

Interval = tuple[int, int]

NO_OUTAGES_TOKENS = frozenset(
    {"-", "немає", "нет", "0", "нема", "відключеньнемає", "безвідключень", "безотключений"}
)
_HEADER_RE = re.compile(r"^(ЦЕК|ДТЕК|DTEK|CEK)\s+(\d{2}\.\d{2}\.\d{4})", re.IGNORECASE)
_QUEUE_RE = re.compile(r"(?:Черга|Група|Очередь|Группа)\s*(\d+(?:\.\d+)?)", re.IGNORECASE)
_TIME_RANGE_RE = re.compile(r"(\d{1,2}:\d{2})\s*[-—–]\s*(\d{1,2}:\d{2})")
_BULK_HEADER_RE = re.compile(r"^([A-ZА-ЯІЇЄ/]+)\s+(\d{2}\.\d{2}\.\d{4})$", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class QueueSchedule:
    """Schedule of one queue for one day. Empty `outages` == no outages."""

    queue: str
    outages: tuple[Interval, ...] = ()

    @property
    def has_outages(self) -> bool:
        return bool(self.outages)


@dataclass(slots=True)
class DaySchedule:
    """Parsed /upload: one company, one date, several queues."""

    company: Company
    day: date
    queues: dict[str, QueueSchedule] = field(default_factory=dict)


class ScheduleParseError(ValueError):
    pass


def parse_date(raw: str) -> date:
    return datetime.strptime(raw.strip(), "%d.%m.%Y").date()


def parse_schedule_text(text: str) -> DaySchedule:
    """Parses the regular upload format::

        ДТЕК 29.01.2026
        Черга 1.1
        00:00-04:00
        12:00-15:00
        Черга 1.2
        -
    """
    lines = (text or "").splitlines()
    if not lines:
        raise ScheduleParseError("empty text")
    match = _HEADER_RE.search(lines[0].strip())
    if not match:
        raise ScheduleParseError("bad header")
    company = Company.parse(match.group(1))
    try:
        day = parse_date(match.group(2))
    except ValueError as e:
        raise ScheduleParseError("bad date") from e

    raw: dict[str, list[Interval]] = {}
    current_queue = ""
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        queue_match = _QUEUE_RE.search(line)
        if queue_match:
            current_queue = queue_match.group(1)
            continue
        if not current_queue:
            continue
        if line.lower().replace(" ", "") in NO_OUTAGES_TOKENS:
            raw.setdefault(current_queue, [])
            continue
        for start, end in _TIME_RANGE_RE.findall(line):
            try:
                interval = normalize_interval(parse_hhmm(start), parse_hhmm(end))
            except ValueError:
                continue
            raw.setdefault(current_queue, []).append(interval)

    result = DaySchedule(company=company, day=day)
    for queue, intervals in raw.items():
        result.queues[queue] = QueueSchedule(queue=queue, outages=tuple(sorted(set(intervals))))
    return result


def parse_bulk_empty(text: str) -> tuple[list[Company], date] | None:
    """Parses the bulk 'no outages for all queues' format::

        ДТЕК/ЦЕК 29.01.2026
        -

    or in one line: ``ДТЕК 29.01.2026 -``. Returns None if the text is not in this format.
    """
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    if len(lines) == 1 and lines[0].endswith(" -"):
        lines = [lines[0][:-2].strip(), "-"]
    if len(lines) < 2 or lines[1] != "-":
        return None
    match = _BULK_HEADER_RE.match(lines[0])
    if not match:
        return None
    companies = []
    for raw in match.group(1).split("/"):
        company = Company.parse(raw)
        if company and company not in companies:
            companies.append(company)
    if not companies:
        return None
    try:
        day = parse_date(match.group(2))
    except ValueError:
        return None
    return companies, day


def empty_day(company: Company, day: date) -> DaySchedule:
    return DaySchedule(
        company=company, day=day, queues={q: QueueSchedule(queue=q) for q in QUEUES}
    )
