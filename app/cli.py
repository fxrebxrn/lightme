"""Management commands.

    python -m app.cli migrate                 # apply DB migrations
    python -m app.cli import-sqlite database.db  # move data from the old SQLite DB
"""

from __future__ import annotations

import argparse
import asyncio

from app.config import DatabaseSettings, LogSettings
from app.core.logging import setup_logging
from app.db.engine import create_engine, create_session_factory
from app.db.migrate import upgrade_head
from app.db.uow import UnitOfWork
from app.services.sqlite_import import import_sqlite


async def _import(path: str) -> None:
    engine = create_engine(DatabaseSettings())
    try:
        async with UnitOfWork(create_session_factory(engine)) as uow:
            report = await import_sqlite(path, uow)
        print(f"Imported: {report}")
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("migrate", help="apply database migrations")
    imp = sub.add_parser("import-sqlite", help="import data from the old SQLite database.db")
    imp.add_argument("path")
    args = parser.parse_args()

    setup_logging(LogSettings().level)
    if args.cmd == "migrate":
        upgrade_head()
        print("Migrations applied")
    elif args.cmd == "import-sqlite":
        upgrade_head()
        asyncio.run(_import(args.path))


if __name__ == "__main__":
    main()
