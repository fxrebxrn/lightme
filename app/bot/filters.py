from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, InlineQuery, Message

from app.i18n import Translator


class IsAdmin(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery | InlineQuery, admin_ids: frozenset[int]) -> bool:
        user = event.from_user
        return bool(user and user.id in admin_ids)


class TextButton(BaseFilter):
    """Matches reply-keyboard buttons in any language.

    `keys`     - exact match with the localized text of these keys;
    `contains` - legacy keyword match (e.g. user typed 'графік').
    """

    def __init__(self, *keys: str, contains: tuple[str, ...] = ()) -> None:
        self.keys = keys
        self.contains = tuple(c.lower() for c in contains)

    async def __call__(self, message: Message, i18n: Translator) -> bool:
        text = message.text
        if not text:
            return False
        for key in self.keys:
            if text in i18n.all_values(key):
                return True
        lowered = text.lower()
        return any(word in lowered for word in self.contains)
