from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.domain.enums import Company, EventKind
from app.domain.intervals import common_light
from app.domain.planner import NotificationPlanner
from app.domain.schedule import parse_bulk_empty, parse_schedule_text

TZ = ZoneInfo("Europe/Kyiv")


def test_parse_regular_schedule():
    s = parse_schedule_text("ДТЕК 29.01.2026\nЧерга 1.1\n00:00-04:00\n12:00 – 15:00\nЧерга 1.2\n-\nЧерга 2.1\n20:00-00:00")
    assert s.company is Company.DTEK and s.day == date(2026, 1, 29)
    assert s.queues["1.1"].outages == ((0, 240), (720, 900))
    assert s.queues["1.2"].outages == ()
    assert s.queues["2.1"].outages == ((1200, 1440),)


def test_parse_header_variants():
    assert parse_schedule_text("цек 01.02.2026\nГрупа 3.2\n1:00-2:30").queues["3.2"].outages == ((60, 150),)
    assert parse_schedule_text("DTEK 01.02.2026").company is Company.DTEK


def test_bulk_empty():
    assert parse_bulk_empty("ДТЕК/ЦЕК 29.01.2026\n-") == ([Company.DTEK, Company.CEK], date(2026, 1, 29))
    assert parse_bulk_empty("ЦЕК 29.01.2026 -") == ([Company.CEK], date(2026, 1, 29))
    assert parse_bulk_empty("ДТЕК 29.01.2026\nЧерга 1.1\n-") is None


def test_common_light():
    assert common_light([(0, 240), (720, 900)], [(180, 360)]) == [(360, 720), (900, 1440)]
    assert common_light([(0, 1440)], []) == []


def _kinds(events):
    return [(e.kind, e.run_at.strftime("%d %H:%M")) for e in events]


def test_planner_basic():
    planner = NotificationPlanner(TZ, 10)
    index = {(Company.DTEK, "1.1"): {date(2026, 1, 29): [(480, 720)]}}
    events = planner.plan(index, datetime(2026, 1, 29, 0, 0, tzinfo=TZ))
    assert _kinds(events) == [
        (EventKind.OFF_REMINDER, "29 07:50"), (EventKind.OFF_NOW, "29 08:00"),
        (EventKind.ON_REMINDER, "29 11:50"), (EventKind.ON_NOW, "29 12:00"),
    ]
    off = events[1]
    assert off.next_at.strftime("%H:%M") == "12:00"
    assert events[3].next_at is None


def test_planner_over_midnight():
    planner = NotificationPlanner(TZ, 10)
    index = {(Company.CEK, "6.2"): {
        date(2026, 1, 29): [(1200, 1440)],
        date(2026, 1, 30): [(0, 180), (600, 660)],
    }}
    events = planner.plan(index, datetime(2026, 1, 29, 12, 0, tzinfo=TZ))
    kinds = _kinds(events)

    assert (EventKind.ON_NOW, "30 00:00") not in kinds
    assert (EventKind.OFF_NOW, "30 00:00") not in kinds
    off = next(e for e in events if e.kind is EventKind.OFF_NOW)
    assert off.event_at.strftime("%d %H:%M") == "29 20:00"
    assert off.next_at.strftime("%d %H:%M") == "30 03:00"
    on = next(e for e in events if e.kind is EventKind.ON_NOW)
    assert on.event_at.strftime("%d %H:%M") == "30 03:00"
    assert on.next_at.strftime("%d %H:%M") == "30 10:00"


def test_planner_skips_past():
    planner = NotificationPlanner(TZ, 10)
    index = {(Company.DTEK, "1.1"): {date(2026, 1, 29): [(480, 720)]}}
    events = planner.plan(index, datetime(2026, 1, 29, 9, 0, tzinfo=TZ))
    assert [e.kind for e in events] == [EventKind.ON_REMINDER, EventKind.ON_NOW]
