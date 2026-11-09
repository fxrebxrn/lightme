from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.domain.enums import BotFlag
from app.services.flags import FlagsService


class TechModeMiddleware(BaseMiddleware):
    """While tech mode is on, only admins can use the bot."""

    async def __call__(self, handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
                       event: TelegramObject, data: dict[str, Any]) -> Any:
        user = data.get("event_from_user")
        if user and user.id in data["admin_ids"]:
            return await handler(event, data)

        flags: FlagsService = data["flags"]
        if not await flags.is_enabled(BotFlag.TECH_MODE):
            return await handler(event, data)

        text = data["t"]("tech_work")
        if isinstance(event, Message):
            await event.answer(text)
        elif isinstance(event, CallbackQuery):

            await event.answer(_strip_html(text)[:200], show_alert=True)
        return None


def _strip_html(text: str) -> str:
    import re

    return re.sub(r"<[^>]+>", "", text)
