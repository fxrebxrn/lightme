from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.db.engine import SessionFactory
from app.db.uow import UnitOfWork


class DbSessionMiddleware(BaseMiddleware):
    """Opens one Unit of Work (DB transaction) per update; commits on success."""

    def __init__(self, session_factory: SessionFactory) -> None:
        self.session_factory = session_factory

    async def __call__(self, handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
                       event: TelegramObject, data: dict[str, Any]) -> Any:
        async with UnitOfWork(self.session_factory) as uow:
            data["uow"] = uow
            return await handler(event, data)
