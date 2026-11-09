"""'Common light' (спільне світло): compare two queues."""

from __future__ import annotations

import re
from datetime import date

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot.callbacks import CmpAction, CmpCb
from app.bot.filters import TextButton
from app.bot.keyboards import user as kb
from app.bot.presenters import compare as view
from app.bot.utils import edit_or_answer
from app.config import Settings
from app.core.clock import Clock
from app.db.models import User
from app.db.uow import UnitOfWork
from app.i18n import Texts
from app.services.compare import CompareService, QueueRef, SaveResult

router = Router(name="user.compare")


def _service(uow: UnitOfWork, settings: Settings) -> CompareService:
    return CompareService(uow, settings.app.max_compares)


def _day(clock: Clock, day: str | None) -> date:
    return clock.tomorrow() if day == "tomorrow" else clock.today()


def _plain(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)[:200]


@router.message(Command("compare"))
@router.message(TextButton("btn_compare"))
async def compare_menu(message: Message, t: Texts) -> None:
    await message.answer(t("cmp_menu_text"), reply_markup=kb.compare_menu(t))


@router.callback_query(CmpCb.filter(F.action == CmpAction.MENU))
async def back_to_menu(call: CallbackQuery, t: Texts) -> None:
    await edit_or_answer(call.message, t("cmp_menu_text"), kb.compare_menu(t))
    await call.answer()


@router.callback_query(CmpCb.filter(F.action == CmpAction.NEW))
async def choose_first_company(call: CallbackQuery, t: Texts) -> None:
    await edit_or_answer(call.message, t("cmp_choose_first"), kb.compare_companies(t))
    await call.answer()


@router.callback_query(CmpCb.filter(F.action == CmpAction.COMPANY1))
async def choose_first_queue(call: CallbackQuery, callback_data: CmpCb, t: Texts) -> None:
    await edit_or_answer(call.message, t("choose_queue", company=callback_data.c1.title),
                         kb.compare_queues(t, callback_data.c1))
    await call.answer()


@router.callback_query(CmpCb.filter(F.action == CmpAction.QUEUE1))
async def choose_second_company(call: CallbackQuery, callback_data: CmpCb, t: Texts) -> None:
    first = (callback_data.c1, callback_data.q1)
    await edit_or_answer(call.message, t("cmp_choose_second"), kb.compare_companies(t, first=first))
    await call.answer()


@router.callback_query(CmpCb.filter(F.action == CmpAction.COMPANY2))
async def choose_second_queue(call: CallbackQuery, callback_data: CmpCb, t: Texts) -> None:
    first = (callback_data.c1, callback_data.q1)
    await edit_or_answer(call.message, t("choose_queue", company=callback_data.c2.title),
                         kb.compare_queues(t, callback_data.c2, first=first))
    await call.answer()


@router.callback_query(CmpCb.filter(F.action == CmpAction.QUEUE2))
async def preview(call: CallbackQuery, callback_data: CmpCb, t: Texts) -> None:
    cb = callback_data
    text = t("cmp_ready_preview", comp1=cb.c1.title, queue1=cb.q1, comp2=cb.c2.title, queue2=cb.q2)
    await edit_or_answer(call.message, text, kb.compare_preview(t, cb))
    await call.answer()


async def _show_result(call: CallbackQuery, cb: CmpCb, day: str, saved_id: int | None, t: Texts,
                       uow: UnitOfWork, settings: Settings, clock: Clock) -> None:
    result = await _service(uow, settings).compare(QueueRef(cb.c1, cb.q1), QueueRef(cb.c2, cb.q2), _day(clock, day))
    if not result.has_data:
        await edit_or_answer(call.message, view.no_data(result, t), kb.compare_no_data(t, cb, day, saved_id))
    elif not result.common:
        await edit_or_answer(call.message, view.no_common(result, t), kb.back_to_compare_menu(t))
    else:
        await edit_or_answer(call.message, view.common_light(result, t), kb.compare_result(t, cb, day, saved_id))


@router.callback_query(CmpCb.filter(F.action == CmpAction.RUN))
async def run(call: CallbackQuery, callback_data: CmpCb, t: Texts, uow: UnitOfWork, settings: Settings,
              clock: Clock) -> None:
    await _show_result(call, callback_data, callback_data.day or "today", callback_data.id, t, uow, settings, clock)
    await call.answer()


@router.callback_query(CmpCb.filter(F.action == CmpAction.DETAILS))
async def details(call: CallbackQuery, callback_data: CmpCb, t: Texts, uow: UnitOfWork, settings: Settings,
                  clock: Clock) -> None:
    cb = callback_data
    day = cb.day or "today"
    result = await _service(uow, settings).compare(QueueRef(cb.c1, cb.q1), QueueRef(cb.c2, cb.q2), _day(clock, day))
    text = view.details(result, t) if result.has_data else view.no_data(result, t)
    await edit_or_answer(call.message, text, kb.compare_back_to_result(t, cb, day, cb.id))
    await call.answer()


@router.callback_query(CmpCb.filter(F.action == CmpAction.SAVE))
async def save(call: CallbackQuery, callback_data: CmpCb, t: Texts, user: User, uow: UnitOfWork,
               settings: Settings) -> None:
    cb = callback_data
    status, name = await _service(uow, settings).save(user.id, QueueRef(cb.c1, cb.q1), QueueRef(cb.c2, cb.q2))
    if status is SaveResult.LIMIT:
        await call.answer(_plain(t("cmp_limit_reached", limit=settings.app.max_compares)), show_alert=True)
        return
    await call.answer(t("cmp_saved_ok"), show_alert=True)
    await edit_or_answer(call.message, t("cmp_saved_msg", name=name), kb.back_to_compare_menu(t))


@router.callback_query(CmpCb.filter(F.action == CmpAction.MY))
async def my_list(call: CallbackQuery, t: Texts, user: User, uow: UnitOfWork, settings: Settings) -> None:
    await _render_saved(call, t, user, uow, settings)
    await call.answer()


async def _render_saved(call: CallbackQuery, t: Texts, user: User, uow: UnitOfWork, settings: Settings) -> None:
    items = await _service(uow, settings).list(user.id)
    if not items:
        await edit_or_answer(call.message, t("cmp_no_saved"), kb.back_to_compare_menu(t))
    else:
        await edit_or_answer(call.message, t("cmp_list_header"), kb.saved_compares(t, items))


@router.callback_query(CmpCb.filter(F.action == CmpAction.SAVED))
async def open_saved(call: CallbackQuery, callback_data: CmpCb, t: Texts, user: User, uow: UnitOfWork,
                     settings: Settings, clock: Clock) -> None:
    item = await _service(uow, settings).get(user.id, callback_data.id or 0)
    if item is None:
        await call.answer(_plain(t("cmp_no_saved")), show_alert=True)
        return
    cb = CmpCb(action=CmpAction.RUN, c1=item.company1, q1=item.queue1, c2=item.company2, q2=item.queue2)
    await _show_result(call, cb, callback_data.day or "today", item.id, t, uow, settings, clock)
    await call.answer()


@router.callback_query(CmpCb.filter(F.action == CmpAction.DELETE))
async def delete(call: CallbackQuery, callback_data: CmpCb, t: Texts, user: User, uow: UnitOfWork,
                 settings: Settings) -> None:
    await _service(uow, settings).delete(user.id, callback_data.id or 0)
    await call.answer(t("cmp_deleted_ok"), show_alert=True)
    await _render_saved(call, t, user, uow, settings)
