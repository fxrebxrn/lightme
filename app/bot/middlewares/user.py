from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from aiogram.types import User as TgUser

from app.db.uow import UnitOfWork
from app.i18n import Translator


class UserMiddleware(BaseMiddleware):
    """Loads/creates the DB user and injects `user` and the localized `t`."""

    async def __call__(self, handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
                       event: TelegramObject, data: dict[str, Any]) -> Any:
        tg_user: TgUser | None = data.get("event_from_user")
        uow: UnitOfWork = data["uow"]
        i18n: Translator = data["i18n"]
        user = None
        if tg_user and not tg_user.is_bot:
            is_inline = isinstance(event, Update) and event.inline_query is not None
            if is_inline:
                user = await uow.users.get(tg_user.id)
            else:
                user = await uow.users.upsert(
                    tg_user.id,
                    username=tg_user.username,
                    full_name=tg_user.full_name,
                    default_language=i18n.default_language.value,
                )
        data["user"] = user
        data["t"] = i18n.for_lang(user.language if user else None)
        return await handler(event, data)
