"""Interval math for 'common light' (спільне світло) comparison."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from app.domain.constants import MINUTES_IN_DAY

Interval = tuple[int, int]


def merge_intervals(intervals: Iterable[Interval]) -> list[Interval]:
    items = sorted(intervals)
    if not items:
        return []
    merged: list[Interval] = []
    cur_s, cur_e = items[0]
    for s, e in items[1:]:
        if s <= cur_e:
            cur_e = max(cur_e, e)
        else:
            merged.append((cur_s, cur_e))
            cur_s, cur_e = s, e
    merged.append((cur_s, cur_e))
    return merged


def invert_intervals(offs: Sequence[Interval], day_minutes: int = MINUTES_IN_DAY) -> list[Interval]:
    """Outages -> periods with light."""
    ons: list[Interval] = []
    prev = 0
    for s, e in offs:
        if prev < s:
            ons.append((prev, s))
        prev = max(prev, e)
    if prev < day_minutes:
        ons.append((prev, day_minutes))
    return ons


def intersect_intervals(a: Sequence[Interval], b: Sequence[Interval]) -> list[Interval]:
    res: list[Interval] = []
    i = j = 0
    while i < len(a) and j < len(b):
        s = max(a[i][0], b[j][0])
        e = min(a[i][1], b[j][1])
        if s < e:
            res.append((s, e))
        if a[i][1] < b[j][1]:
            i += 1
        else:
            j += 1
    return res


def common_light(offs1: Iterable[Interval], offs2: Iterable[Interval]) -> list[Interval]:
    """Intervals when both queues have light."""
    ons1 = invert_intervals(merge_intervals(offs1))
    ons2 = invert_intervals(merge_intervals(offs2))
    common = intersect_intervals(ons1, ons2)

    return [(s, e) for s, e in common if e - s > 0 and not (s == MINUTES_IN_DAY - 1 and e == MINUTES_IN_DAY)]


def total_minutes(intervals: Iterable[Interval]) -> int:
    return sum(max(0, e - s) for s, e in intervals)
