from __future__ import annotations

from datetime import date, timedelta

from aiogram.types import ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from app.domain.enums import Company


def admin_menu(today: date) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    for day in (today, today + timedelta(days=1)):
        for company in Company:
            kb.button(text=f"/upload {company.title} {day:%d.%m.%Y} -")
    for cmd in ("/avaron", "/avaroff", "/techon", "/techoff", "/getdb", "/stats"):
        kb.button(text=cmd)
    kb.adjust(len(Company), len(Company), 2, 2, 2)
    return kb.as_markup(resize_keyboard=True)
