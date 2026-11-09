from __future__ import annotations

from datetime import date

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot.callbacks import CompanyCb, CompanyListCb, Mode, ScheduleCb
from app.bot.filters import TextButton
from app.bot.keyboards import user as kb
from app.bot.presenters.schedule import schedule_card
from app.bot.utils import edit_or_answer
from app.core.clock import Clock
from app.db.models import User
from app.db.uow import UnitOfWork
from app.domain.constants import QUEUES
from app.domain.enums import BotFlag
from app.i18n import Texts
from app.services.flags import FlagsService
from app.services.schedules import ScheduleService

router = Router(name="user.schedules")


async def _companies_markup(mode: Mode, user: User, uow: UnitOfWork, clock: Clock):
    subs = await uow.subscriptions.list_for_user(user.id) if mode is Mode.VIEW else []
    return kb.companies(mode, subs, clock.today())


@router.message(Command("sched"))
@router.message(TextButton("btn_schedules", contains=("графік", "график")))
async def schedules_start(message: Message, t: Texts, user: User, uow: UnitOfWork, clock: Clock) -> None:
    await message.answer(t("choose_comp"), reply_markup=await _companies_markup(Mode.VIEW, user, uow, clock))


@router.callback_query(CompanyListCb.filter())
async def back_to_companies(call: CallbackQuery, callback_data: CompanyListCb, t: Texts, user: User,
                            uow: UnitOfWork, clock: Clock) -> None:
    markup = await _companies_markup(callback_data.mode, user, uow, clock)
    await edit_or_answer(call.message, t("choose_comp"), markup)
    await call.answer()


@router.callback_query(CompanyCb.filter())
async def choose_company(call: CallbackQuery, callback_data: CompanyCb, t: Texts, clock: Clock) -> None:
    await edit_or_answer(
        call.message,
        t("choose_queue", company=callback_data.company.title),
        kb.queues(callback_data.mode, callback_data.company, clock.today(), t),
    )
    await call.answer()


@router.callback_query(ScheduleCb.filter())
async def show_schedule(call: CallbackQuery, callback_data: ScheduleCb, t: Texts, uow: UnitOfWork,
                        clock: Clock, flags: FlagsService) -> None:
    if callback_data.queue not in QUEUES:
        await call.answer(t("invalid_data"), show_alert=True)
        return
    try:
        day = date.fromisoformat(callback_data.day)
    except ValueError:
        day = clock.today()
    view = await ScheduleService(uow).get_day(callback_data.company, callback_data.queue, day)
    text = schedule_card(view, now=clock.now(), emergency=await flags.is_enabled(BotFlag.EMERGENCY), t=t)
    markup = kb.schedule(callback_data.company, callback_data.queue, day, clock.today(), clock.tomorrow(), t)
    await edit_or_answer(call.message, text, markup)
    await call.answer()
