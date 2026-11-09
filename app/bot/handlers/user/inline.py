from __future__ import annotations

import hashlib

from aiogram import Router
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent

from app.bot.presenters.schedule import inline_schedule
from app.core.clock import Clock
from app.db.uow import UnitOfWork
from app.domain.enums import Company
from app.i18n import Texts
from app.services.schedules import ScheduleService

router = Router(name="user.inline")

_TOMORROW_WORDS = ("завтра",)


@router.inline_query()
async def inline_schedule_query(query: InlineQuery, t: Texts, uow: UnitOfWork, clock: Clock) -> None:
    """@bot ДТЕК 1.1 [завтра]"""
    text = query.query.strip().lower()
    parts = text.split()
    if len(parts) < 2:
        return
    company = Company.parse(parts[0])
    if company is None:
        return
    queue = parts[1]
    tomorrow = any(word in text for word in _TOMORROW_WORDS)
    day = clock.tomorrow() if tomorrow else clock.today()

    view = await ScheduleService(uow).get_day(company, queue, day)
    day_label = t("inline_tomorrow") if tomorrow else t("inline_today")
    result_id = hashlib.md5(f"{company}:{queue}:{day}".encode()).hexdigest()
    item = InlineQueryResultArticle(
        id=result_id,
        title=t("inline_title", company=company.title, queue=queue, day_label=day_label),
        description=t("inline_description"),
        input_message_content=InputTextMessageContent(
            message_text=inline_schedule(view, t), parse_mode="HTML", disable_web_page_preview=True,
        ),
    )
    await query.answer(results=[item], cache_time=60)
