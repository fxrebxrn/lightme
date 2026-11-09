"""Test infrastructure.

Integration tests need a PostgreSQL database: set TEST_DATABASE_URL, e.g.
    TEST_DATABASE_URL=postgresql+asyncpg://lightme:lightme@localhost:5432/lightme_test
They are skipped if it's not set.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from itertools import count
from typing import Any

import pytest
import pytest_asyncio
from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.methods import TelegramMethod
from aiogram.types import Chat, Message, MessageId
from aiogram.types import User as TgUser
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

os.environ.setdefault("BOT_TOKEN", "42:TEST")
os.environ.setdefault("ADMIN_IDS", "1")

TEST_DB = os.environ.get("TEST_DATABASE_URL")


class MockedSession(BaseSession):
    """Records every Bot API call instead of sending it."""

    def __init__(self) -> None:
        super().__init__()
        self.requests: list[TelegramMethod] = []
        self._ids = count(1000)

    async def make_request(self, bot: Bot, method: TelegramMethod, timeout: int | None = None) -> Any:
        self.requests.append(method)
        returning = method.__returning__
        if returning is bool:
            return True
        if returning is MessageId:
            return MessageId(message_id=next(self._ids))
        if returning is TgUser:
            return TgUser(id=42, is_bot=True, first_name="LightMe", username="lightme_test_bot")
        chat_id = getattr(method, "chat_id", None) or 1
        return Message(
            message_id=next(self._ids), date=datetime.now(UTC),
            chat=Chat(id=chat_id, type="private"), text=getattr(method, "text", None),
        ).as_(bot)

    async def stream_content(self, *args, **kwargs):
        yield b""

    async def close(self) -> None:
        pass

    def texts(self) -> list[str]:
        return [getattr(r, "text", None) or "" for r in self.requests]

    def clear(self) -> None:
        self.requests.clear()


@pytest.fixture
def mocked_session() -> MockedSession:
    return MockedSession()


@pytest_asyncio.fixture
async def db_url():
    if not TEST_DB:
        pytest.skip("TEST_DATABASE_URL is not set")
    from alembic import command

    from app.db.migrate import alembic_config

    engine = create_async_engine(TEST_DB)
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
    await engine.dispose()
    cfg = alembic_config()
    cfg.attributes["url"] = TEST_DB
    import asyncio

    await asyncio.to_thread(command.upgrade, cfg, "head")
    yield TEST_DB
