from __future__ import annotations

import logging

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InaccessibleMessage, InlineKeyboardMarkup, Message

log = logging.getLogger(__name__)


async def edit_or_answer(message: Message | InaccessibleMessage | None, text: str,
                         reply_markup: InlineKeyboardMarkup | None = None) -> None:
    """Edits a bot message in place; falls back to a new message if it can't be edited."""
    if message is None:
        return
    if isinstance(message, Message):
        try:
            await message.edit_text(text, reply_markup=reply_markup, disable_web_page_preview=True)
            return
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                return
            log.debug("edit failed, sending new message: %s", e)
    await message.bot.send_message(message.chat.id, text, reply_markup=reply_markup,
                                   disable_web_page_preview=True)
