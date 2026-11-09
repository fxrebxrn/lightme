"""Keyboards of the user part of the bot."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from app.bot.callbacks import (
    CmpAction,
    CmpCb,
    CompanyCb,
    CompanyListCb,
    LangCb,
    MenuCb,
    Mode,
    NotifyCb,
    ScheduleCb,
    SettingsCb,
    SubscribeCb,
    UnsubscribeCb,
)
from app.db.models import Compare, Subscription, User
from app.domain.constants import QUEUES
from app.domain.enums import NOTIFY_FIELDS, Company, Language
from app.i18n import Texts

_NOTIFY_LABELS = {
    "notify_off": "notif_label_off",
    "notify_on": "notif_label_on",
    "notify_off_10": "notif_label_off_10",
    "notify_on_10": "notif_label_on_10",
}


def language() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🇺🇦 Українська", callback_data=LangCb(code=Language.UK))
    kb.button(text="🇷🇺 Русский", callback_data=LangCb(code=Language.RU))
    kb.adjust(2)
    return kb.as_markup()


def subscribe_channel(t: Texts, channel_url: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if channel_url:
        kb.button(text=t("sub_btn"), url=channel_url)
    kb.button(text=t("continue_btn"), callback_data=MenuCb(action="start"))
    kb.adjust(1)
    return kb.as_markup()


def main_menu(t: Texts) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    for key in ("btn_add_queue", "btn_my_queues", "btn_schedules", "btn_compare", "btn_settings", "btn_support"):
        kb.button(text=t(key))
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)


def companies(mode: Mode, subs: Sequence[Subscription] = (), today: date | None = None) -> InlineKeyboardMarkup:
    """Company choice. In view mode user's own queues are shown as shortcuts."""
    kb = InlineKeyboardBuilder()
    for company in Company:
        kb.button(text=company.title, callback_data=CompanyCb(mode=mode, company=company))
    sizes = [len(Company)]
    if mode is Mode.VIEW and today:
        for sub in subs:
            kb.button(
                text=f"{sub.company.title} {sub.queue}",
                callback_data=ScheduleCb(company=sub.company, queue=sub.queue, day=today.isoformat()),
            )
            sizes.append(1)
    kb.adjust(*sizes)
    return kb.as_markup()


def queues(mode: Mode, company: Company, today: date, t: Texts) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for queue in QUEUES:
        if mode is Mode.VIEW:
            kb.button(text=queue, callback_data=ScheduleCb(company=company, queue=queue, day=today.isoformat()))
        else:
            kb.button(text=queue, callback_data=SubscribeCb(company=company, queue=queue))
    kb.button(text=t("back"), callback_data=CompanyListCb(mode=mode))
    kb.adjust(*([3] * (len(QUEUES) // 3)), 1)
    return kb.as_markup()


def schedule(company: Company, queue: str, shown_day: date, today: date, tomorrow: date,
             t: Texts) -> InlineKeyboardMarkup:
    if shown_day == today:
        switch = InlineKeyboardButton(
            text=t("tomorrow_label"), style="primary",
            callback_data=ScheduleCb(company=company, queue=queue, day=tomorrow.isoformat()).pack(),
        )
    else:
        switch = InlineKeyboardButton(
            text=t("today_label"), style="primary",
            callback_data=ScheduleCb(company=company, queue=queue, day=today.isoformat()).pack(),
        )
    back = InlineKeyboardButton(
        text=t("back"), style="danger", callback_data=CompanyCb(mode=Mode.VIEW, company=company).pack()
    )
    return InlineKeyboardMarkup(inline_keyboard=[[switch], [back]])


def my_queues(subs: Sequence[Subscription]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"🗑 {s.company.title} {s.queue}", style="danger",
            callback_data=UnsubscribeCb(id=s.id).pack(),
        )]
        for s in subs
    ])



def settings(t: Texts) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=t("btn_lang_switch"), callback_data=SettingsCb(action="lang"))
    kb.button(text=t("btn_notifications"), callback_data=SettingsCb(action="notif"))
    kb.button(text=t("btn_toggle_all"), callback_data=SettingsCb(action="all"))
    kb.adjust(1)
    return kb.as_markup()


def notifications(user: User, t: Texts) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for field in NOTIFY_FIELDS:
        state = "✅" if getattr(user, field) else "❌"
        kb.button(text=f"{t(_NOTIFY_LABELS[field])}: {state}", callback_data=NotifyCb(field=field))
    kb.button(text=t("back"), callback_data=SettingsCb(action="back"))
    kb.adjust(1)
    return kb.as_markup()



def compare_menu(t: Texts) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=t("btn_compare_new"), callback_data=CmpCb(action=CmpAction.NEW))
    kb.button(text=t("btn_compare_my"), callback_data=CmpCb(action=CmpAction.MY))
    kb.adjust(1)
    return kb.as_markup()


def back_to_compare_menu(t: Texts) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=t("back"), callback_data=CmpCb(action=CmpAction.MENU))
    return kb.as_markup()


def compare_companies(t: Texts, *, first: tuple[Company, str] | None = None) -> InlineKeyboardMarkup:
    """Company choice for pair item #1 (first=None) or #2."""
    kb = InlineKeyboardBuilder()
    for company in Company:
        if first is None:
            cb = CmpCb(action=CmpAction.COMPANY1, c1=company)
        else:
            cb = CmpCb(action=CmpAction.COMPANY2, c1=first[0], q1=first[1], c2=company)
        kb.button(text=company.title, callback_data=cb)
    back = CmpCb(action=CmpAction.MENU) if first is None else CmpCb(action=CmpAction.NEW)
    kb.button(text=t("back"), callback_data=back)
    kb.adjust(len(Company), 1)
    return kb.as_markup()


def compare_queues(t: Texts, company: Company, *, first: tuple[Company, str] | None = None) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for queue in QUEUES:
        if first is None:
            cb = CmpCb(action=CmpAction.QUEUE1, c1=company, q1=queue)
        else:
            cb = CmpCb(action=CmpAction.QUEUE2, c1=first[0], q1=first[1], c2=company, q2=queue)
        kb.button(text=queue, callback_data=cb)
    if first is None:
        back = CmpCb(action=CmpAction.NEW)
    else:
        back = CmpCb(action=CmpAction.QUEUE1, c1=first[0], q1=first[1])
    kb.button(text=t("back"), callback_data=back)
    kb.adjust(*([3] * (len(QUEUES) // 3)), 1)
    return kb.as_markup()


def _pair(cb: CmpCb, **kwargs) -> CmpCb:
    return CmpCb(c1=cb.c1, q1=cb.q1, c2=cb.c2, q2=cb.q2, **kwargs)


def compare_preview(t: Texts, cb: CmpCb) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=t("today_label"), callback_data=_pair(cb, action=CmpAction.RUN, day="today"))
    kb.button(text=t("tomorrow_label"), callback_data=_pair(cb, action=CmpAction.RUN, day="tomorrow"))
    kb.button(text=t("cmp_save_button"), callback_data=_pair(cb, action=CmpAction.SAVE))
    kb.button(text=t("back"), callback_data=CmpCb(action=CmpAction.QUEUE1, c1=cb.c1, q1=cb.q1))
    kb.adjust(2, 1, 1)
    return kb.as_markup()


def compare_result(t: Texts, cb: CmpCb, day: str, saved_id: int | None) -> InlineKeyboardMarkup:
    other = "tomorrow" if day == "today" else "today"
    other_label = t("tomorrow_label") if other == "tomorrow" else t("today_label")
    rows = [
        [InlineKeyboardButton(text=t("cmp_details_button"),
                              callback_data=_pair(cb, action=CmpAction.DETAILS, day=day, id=saved_id).pack())],
        [InlineKeyboardButton(text=t("toggle_day_label", day=other_label), style="primary",
                              callback_data=_pair(cb, action=CmpAction.RUN, day=other, id=saved_id).pack())],
    ]
    if saved_id:
        rows.append([InlineKeyboardButton(text=t("cmp_delete_saved"),
                                          callback_data=CmpCb(action=CmpAction.DELETE, id=saved_id).pack())])
    else:
        rows.append([InlineKeyboardButton(text=t("cmp_save_button"),
                                          callback_data=_pair(cb, action=CmpAction.SAVE).pack())])
    rows.append([InlineKeyboardButton(text=t("back"), callback_data=CmpCb(action=CmpAction.MENU).pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def compare_no_data(t: Texts, cb: CmpCb, day: str, saved_id: int | None) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if day == "tomorrow":
        kb.button(text=t("today_label"), callback_data=_pair(cb, action=CmpAction.RUN, day="today", id=saved_id))
    kb.button(text=t("back"), callback_data=CmpCb(action=CmpAction.MENU))
    kb.adjust(1)
    return kb.as_markup()


def compare_back_to_result(t: Texts, cb: CmpCb, day: str, saved_id: int | None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(
        text=t("back"), style="danger",
        callback_data=_pair(cb, action=CmpAction.RUN, day=day, id=saved_id).pack(),
    )]])


def saved_compares(t: Texts, items: Sequence[Compare]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for item in items:
        kb.button(text=item.name, callback_data=CmpCb(action=CmpAction.SAVED, id=item.id, day="today"))
    kb.button(text=t("back"), callback_data=CmpCb(action=CmpAction.MENU))
    kb.adjust(1)
    return kb.as_markup()
