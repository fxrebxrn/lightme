from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot.callbacks import Mode, SubscribeCb, UnsubscribeCb
from app.bot.filters import TextButton
from app.bot.keyboards import user as kb
from app.bot.utils import edit_or_answer
from app.config import Settings
from app.db.models import User
from app.db.uow import UnitOfWork
from app.i18n import Texts
from app.services.subscriptions import AddResult, SubscriptionService

router = Router(name="user.subscriptions")


def _service(uow: UnitOfWork, settings: Settings) -> SubscriptionService:
    return SubscriptionService(uow, settings.app.max_subscriptions)


@router.message(Command("add"))
@router.message(TextButton("btn_add_queue", contains=("додати", "добавить")))
async def add_queue(message: Message, t: Texts) -> None:
    await message.answer(t("choose_comp"), reply_markup=kb.companies(Mode.SUB))


@router.callback_query(SubscribeCb.filter())
async def subscribe(call: CallbackQuery, callback_data: SubscribeCb, t: Texts, user: User,
                    uow: UnitOfWork, settings: Settings) -> None:
    result = await _service(uow, settings).add(user.id, callback_data.company, callback_data.queue)
    if result is AddResult.ADDED:
        text = t("added", company=callback_data.company.title, queue=callback_data.queue)
    elif result is AddResult.LIMIT:
        text = _plain(t("subs_limit_reached", limit=settings.app.max_subscriptions))
    elif result is AddResult.INVALID:
        text = t("invalid_data")
    else:
        text = t("exists")
    await call.answer(text, show_alert=True)


@router.message(Command("subs"))
@router.message(TextButton("btn_my_queues", contains=("мої чер", "мои оче")))
async def my_queues(message: Message, t: Texts, user: User, uow: UnitOfWork, settings: Settings) -> None:
    subs = await _service(uow, settings).list(user.id)
    if not subs:
        await message.answer(t("empty_list"))
        return
    await message.answer(t("my_que"), reply_markup=kb.my_queues(subs))


@router.callback_query(UnsubscribeCb.filter())
async def unsubscribe(call: CallbackQuery, callback_data: UnsubscribeCb, t: Texts, user: User,
                      uow: UnitOfWork, settings: Settings) -> None:
    service = _service(uow, settings)
    await service.remove(user.id, callback_data.id)
    await call.answer(t("deleted"))
    subs = await service.list(user.id)
    if subs:
        await edit_or_answer(call.message, t("my_que"), kb.my_queues(subs))
    else:
        await edit_or_answer(call.message, t("empty_list"))


def _plain(text: str) -> str:
    """Alerts don't support HTML / custom emoji."""
    import re

    return re.sub(r"<[^>]+>", "", text)[:200]
