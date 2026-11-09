"""Import of the old SQLite database (database.db) into PostgreSQL.

Used by `python -m app.cli import-sqlite database.db` and by the admin
command /importdb. Import is idempotent: running it twice doesn't duplicate data.
"""

from __future__ import annotations

import logging
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.db.models import Compare, Subscription, User
from app.db.uow import UnitOfWork
from app.domain.enums import BotFlag, Company, Language
from app.domain.timeutils import normalize_interval, parse_hhmm

log = logging.getLogger(__name__)


@dataclass
class ImportReport:
    users: int = 0
    subscriptions: int = 0
    schedules: int = 0
    compares: int = 0
    skipped: int = 0

    def __str__(self) -> str:
        return (f"users={self.users}, subscriptions={self.subscriptions}, schedules={self.schedules}, "
                f"compares={self.compares}, skipped={self.skipped}")


def _tables(conn: sqlite3.Connection) -> set[str]:
    return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}


def _flag(value) -> bool:
    return value is None or str(value).strip() not in ("0", "", "false", "False")


def _parse_ts(raw) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.strptime(str(raw)[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
    except ValueError:
        return None


async def import_sqlite(path: str | Path, uow: UnitOfWork) -> ImportReport:
    report = ImportReport()
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        tables = _tables(conn)
        session = uow.session


        users: dict[int, dict] = {}
        if "user_prefs" in tables:
            cols = _columns(conn, "user_prefs")
            for row in conn.execute("SELECT * FROM user_prefs"):
                data = {"id": int(row["user_id"]), "language": Language.parse(row["language"]).value}
                for field in ("notify_off", "notify_on", "notify_off_10", "notify_on_10"):
                    data[field] = _flag(row[field]) if field in cols else True
                users[data["id"]] = data
        extra_ids = set()
        if "users" in tables:
            extra_ids |= {int(r[0]) for r in conn.execute("SELECT DISTINCT user_id FROM users") if r[0] is not None}
        if "compares" in tables:
            extra_ids |= {int(r[0]) for r in conn.execute("SELECT DISTINCT user_id FROM compares") if r[0] is not None}
        for uid in extra_ids - users.keys():
            users[uid] = {"id": uid, "language": "uk"}
        for data in users.values():
            update = {k: v for k, v in data.items() if k != "id"}
            await session.execute(
                insert(User).values(**data).on_conflict_do_update(index_elements=[User.id], set_=update)
            )
        report.users = len(users)


        if "users" in tables:
            for row in conn.execute("SELECT user_id, company, queue FROM users"):
                company = Company.parse(row["company"] or "")
                if company is None or not row["queue"]:
                    report.skipped += 1
                    continue
                res = await session.execute(
                    insert(Subscription)
                    .values(user_id=int(row["user_id"]), company=company, queue=str(row["queue"]))
                    .on_conflict_do_nothing(index_elements=["user_id", "company", "queue"])
                    .returning(Subscription.id)
                )
                report.subscriptions += 1 if res.scalar() else 0


        if "schedules" in tables:
            grouped: dict[tuple[Company, str, date], dict] = defaultdict(lambda: {"intervals": set(), "ts": None})
            for row in conn.execute("SELECT company, queue, date, off_time, on_time, created_at FROM schedules"):
                company = Company.parse(row["company"] or "")
                try:
                    day = date.fromisoformat(row["date"])
                except (TypeError, ValueError):
                    company = None
                if company is None or not row["queue"]:
                    report.skipped += 1
                    continue
                item = grouped[(company, str(row["queue"]), day)]
                ts = _parse_ts(row["created_at"])
                if ts and (item["ts"] is None or ts > item["ts"]):
                    item["ts"] = ts
                if row["off_time"] in (None, "empty", "-"):
                    continue
                try:
                    item["intervals"].add(normalize_interval(parse_hhmm(row["off_time"]), parse_hhmm(row["on_time"])))
                except ValueError:
                    report.skipped += 1
            for (company, queue, day), item in grouped.items():
                schedule = await uow.schedules.replace_queue(company, queue, day, sorted(item["intervals"]))
                if item["ts"]:
                    schedule.updated_at = item["ts"]
                report.schedules += 1


        if "compares" in tables:
            for row in conn.execute("SELECT * FROM compares ORDER BY id"):
                c1, c2 = Company.parse(row["comp1"] or ""), Company.parse(row["comp2"] or "")
                if not c1 or not c2:
                    report.skipped += 1
                    continue
                exists = await session.scalar(select(Compare.id).where(
                    Compare.user_id == int(row["user_id"]), Compare.company1 == c1, Compare.queue1 == row["queue1"],
                    Compare.company2 == c2, Compare.queue2 == row["queue2"],
                ))
                if exists:
                    continue
                session.add(Compare(
                    user_id=int(row["user_id"]), company1=c1, queue1=row["queue1"], company2=c2,
                    queue2=row["queue2"], name=f"{c1.title} {row['queue1']} + {c2.title} {row['queue2']}",
                ))
                report.compares += 1


        if "bot_settings" in tables:
            for row in conn.execute("SELECT key, value FROM bot_settings"):
                if row["key"] == "avaron":
                    await uow.bot_settings.set(BotFlag.EMERGENCY, str(row["value"]) == "1")
                elif row["key"] == "tech_mode":
                    await uow.bot_settings.set(BotFlag.TECH_MODE, str(row["value"]) == "1")
        if "settings" in tables:
            for row in conn.execute("SELECT key, status FROM settings"):
                if row["key"] == "tech_mode":
                    await uow.bot_settings.set(BotFlag.TECH_MODE, row["status"] == 1)

        await session.flush()
    finally:
        conn.close()
    log.info("SQLite import finished: %s", report)
    return report


__all__ = ["ImportReport", "import_sqlite"]
