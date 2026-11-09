"""Database export for the admin (/getdb)."""

from __future__ import annotations

import asyncio
import gzip
import json
import shutil
import tempfile
from datetime import date, datetime
from enum import Enum
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.engine import make_url

from app.db.base import Base
from app.db.uow import UnitOfWork


def _default(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    return str(value)


async def export_json(uow: UnitOfWork) -> Path:
    """All tables -> gzipped JSON file. Works everywhere (no extra binaries)."""
    data: dict[str, list[dict]] = {}
    for table in Base.metadata.sorted_tables:
        rows = await uow.session.execute(select(table))
        data[table.name] = [dict(r._mapping) for r in rows]
    path = Path(tempfile.mkdtemp()) / f"lightme_{datetime.now():%Y%m%d_%H%M%S}.json.gz"
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, default=_default, indent=1)
    return path


async def export_pg_dump(dsn: str) -> Path | None:
    """Full SQL dump via pg_dump if it is installed (it is in the Docker image)."""
    if not shutil.which("pg_dump"):
        return None
    url = make_url(dsn).set(drivername="postgresql")
    path = Path(tempfile.mkdtemp()) / f"lightme_{datetime.now():%Y%m%d_%H%M%S}.sql.gz"
    proc = await asyncio.create_subprocess_exec(
        "pg_dump", "--no-owner", "--no-privileges", "--compress=6", "--file", str(path),
        "--dbname", url.render_as_string(hide_password=False),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(stderr.decode(errors="ignore")[:500])
    return path
