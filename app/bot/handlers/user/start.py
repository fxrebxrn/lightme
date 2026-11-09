from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from app.bot.callbacks import LangCb, MenuCb
from app.bot.filters import TextButton
from app.bot.keyboards import user as kb
from app.bot.utils import edit_or_answer
from app.config import Settings
from app.core.clock import Clock
from app.db.models import User
from app.db.uow import UnitOfWork
from app.domain.enums import Language
from app.i18n import Texts, Translator
from app.services.users import UserSettingsService

router = Router(name="user.start")


@router.message(CommandStart())
async def start(message: Message, i18n: Translator) -> None:
    await message.answer(i18n.for_lang(Language.UK)("select_lang"), reply_markup=kb.language())


@router.callback_query(LangCb.filter())
async def set_language(call: CallbackQuery, callback_data: LangCb, user: User, uow: UnitOfWork,
                       i18n: Translator, settings: Settings) -> None:
    lang = Language.parse(callback_data.code)
    await UserSettingsService(uow).set_language(user, lang)
    t = i18n.for_lang(lang)
    await edit_or_answer(call.message, t("lang_set"))
    await call.message.answer(t("sub_recommend"), reply_markup=kb.subscribe_channel(t, settings.bot.channel_url),
                              disable_web_page_preview=True)
    await call.answer()


@router.callback_query(MenuCb.filter(F.action == "start"))
async def menu_from_button(call: CallbackQuery, t: Texts) -> None:
    await call.message.answer(t("menu_main"), reply_markup=kb.main_menu(t))
    await call.answer()


@router.message(Command("menu"))
@router.message(F.reply_to_message.is_(None), TextButton("back"))
async def menu(message: Message, t: Texts) -> None:
    await message.answer(t("menu_main"), reply_markup=kb.main_menu(t))


@router.message(Command("check"))
async def server_time(message: Message, clock: Clock) -> None:
    await message.answer(f"Server time ({clock.tz}): {clock.now():%d.%m.%Y %H:%M:%S}")
