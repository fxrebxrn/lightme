"""Run Alembic migrations programmatically (used on bot start)."""

from __future__ import annotations

import asyncio

from alembic import command
from alembic.config import Config

from app.config import BASE_DIR


def alembic_config() -> Config:
    cfg = Config(str(BASE_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BASE_DIR / "migrations"))
    cfg.attributes["skip_logging"] = True
    return cfg


def upgrade_head() -> None:
    command.upgrade(alembic_config(), "head")


async def upgrade_head_async() -> None:

    await asyncio.to_thread(upgrade_head)
