from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.bot.filters import TextButton
from app.config import Settings
from app.i18n import Texts

router = Router(name="user.support")


@router.message(Command("support"))
@router.message(TextButton("btn_support"))
async def support(message: Message, t: Texts, settings: Settings) -> None:
    await message.answer(
        t("support_text", user=settings.bot.support_username, url=settings.bot.donate_url),
        disable_web_page_preview=True,
    )
