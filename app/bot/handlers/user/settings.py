from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot.callbacks import NotifyCb, SettingsCb
from app.bot.filters import TextButton
from app.bot.keyboards import user as kb
from app.bot.utils import edit_or_answer
from app.db.models import User
from app.db.uow import UnitOfWork
from app.domain.enums import NOTIFY_FIELDS
from app.i18n import Texts
from app.services.users import UserSettingsService

router = Router(name="user.settings")


@router.message(Command("settings"))
@router.message(TextButton("btn_settings"))
async def settings_menu(message: Message, t: Texts) -> None:
    await message.answer(t("settings_text"), reply_markup=kb.settings(t))


@router.callback_query(SettingsCb.filter())
async def settings_action(call: CallbackQuery, callback_data: SettingsCb, t: Texts, user: User,
                          uow: UnitOfWork) -> None:
    action = callback_data.action
    if action == "lang":
        await call.message.answer(t("select_lang"), reply_markup=kb.language())
    elif action == "notif":
        await edit_or_answer(call.message, t("notifications_text"), kb.notifications(user, t))
    elif action == "all":
        enabled = await UserSettingsService(uow).toggle_all(user)
        await call.answer(t("notif_all_set", state=t("state_on") if enabled else t("state_off")))
        await edit_or_answer(call.message, t("notifications_text"), kb.notifications(user, t))
        return
    elif action == "back":
        await edit_or_answer(call.message, t("settings_text"), kb.settings(t))
    await call.answer()


@router.callback_query(NotifyCb.filter())
async def toggle_notification(call: CallbackQuery, callback_data: NotifyCb, t: Texts, user: User,
                              uow: UnitOfWork) -> None:
    if callback_data.field not in NOTIFY_FIELDS:
        await call.answer(t("invalid_data"), show_alert=True)
        return
    await UserSettingsService(uow).toggle(user, callback_data.field)
    await edit_or_answer(call.message, t("notifications_text"), kb.notifications(user, t))
    await call.answer()
