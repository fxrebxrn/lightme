from __future__ import annotations

from aiogram import Router
from aiogram.types import CallbackQuery

from app.i18n import Texts

router = Router(name="user.fallback")


@router.callback_query()
async def outdated_button(call: CallbackQuery, t: Texts) -> None:
    """Buttons from old messages (before the update) or unknown data."""
    await call.answer(t("outdated_button"), show_alert=True)
