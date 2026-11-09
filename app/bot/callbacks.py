"""Typed callback data (aiogram CallbackData factories).

Telegram limits callback_data to 64 bytes, so prefixes are short and
companies are encoded by their latin code (DTEK / CEK).
"""

from __future__ import annotations

from enum import StrEnum

from aiogram.filters.callback_data import CallbackData

from app.domain.enums import Company


class Mode(StrEnum):
    VIEW = "v"
    SUB = "s"


class LangCb(CallbackData, prefix="lang"):
    code: str


class MenuCb(CallbackData, prefix="menu"):
    action: str


class CompanyListCb(CallbackData, prefix="cl"):
    mode: Mode


class CompanyCb(CallbackData, prefix="co"):
    mode: Mode
    company: Company


class SubscribeCb(CallbackData, prefix="sub"):
    company: Company
    queue: str


class UnsubscribeCb(CallbackData, prefix="uns"):
    id: int


class ScheduleCb(CallbackData, prefix="sch"):
    company: Company
    queue: str
    day: str


class SettingsCb(CallbackData, prefix="st"):
    action: str


class NotifyCb(CallbackData, prefix="nt"):
    field: str


class CmpAction(StrEnum):
    MENU = "menu"
    NEW = "new"
    MY = "my"
    COMPANY1 = "c1"
    QUEUE1 = "q1"
    COMPANY2 = "c2"
    QUEUE2 = "q2"
    RUN = "run"
    DETAILS = "det"
    SAVE = "save"
    SAVED = "sv"
    DELETE = "del"


class CmpCb(CallbackData, prefix="cmp"):
    action: CmpAction
    c1: Company | None = None
    q1: str | None = None
    c2: Company | None = None
    q2: str | None = None
    day: str | None = None
    id: int | None = None
