"""/upload - schedule upload by admin."""

from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from app.bot.notifications.scheduler import NotificationScheduler
from app.bot.notifications.updates import ScheduleUpdateNotifier
from app.bot.presenters.formatting import GREEN, RED, fmt_date
from app.bot.tasks import BackgroundTasks
from app.db.uow import UnitOfWork
from app.domain.schedule import ScheduleParseError, empty_day, parse_bulk_empty, parse_schedule_text
from app.domain.timeutils import fmt_minute
from app.services.schedules import ScheduleService, UploadResult

router = Router(name="admin.upload")
log = logging.getLogger(__name__)


def _summary(result: UploadResult) -> str:
    company = result.company.title
    blocks = []
    for queue, item in result.schedule.queues.items():
        icon = "🔔" if queue in result.changed else "🔕 (без змін)"
        if not item.has_outages:
            blocks.append(f"{company} {queue} {icon}:\nВідключень немає")
        else:
            lines = [f"{RED} {fmt_minute(s)} - {GREEN} {fmt_minute(e)}" for s, e in item.outages]
            blocks.append(f"{company} {queue} {icon}:\n" + "\n".join(lines))
    return "\n\n".join(blocks)


async def _after_save(results: list[UploadResult], notifications: NotificationScheduler,
                      update_notifier: ScheduleUpdateNotifier) -> None:
    await notifications.rebuild()
    for result in results:
        if result.changed:
            await update_notifier.notify(result)


@router.message(Command("upload"))
async def upload(message: Message, command: CommandObject, uow: UnitOfWork,
                 notifications: NotificationScheduler, update_notifier: ScheduleUpdateNotifier,
                 tasks: BackgroundTasks) -> None:
    raw = (command.args or "").strip()
    service = ScheduleService(uow)

    bulk = parse_bulk_empty(raw)
    if bulk:
        companies, day = bulk
        results = [await service.apply_upload(empty_day(company, day), force=True) for company in companies]
        await uow.commit()
        tasks.spawn(_after_save(results, notifications, update_notifier))
        changed = sum(len(r.changed) for r in results)
        names = ", ".join(c.title for c in companies)
        await message.answer(
            f"Всі графіки для <b>{names}</b> на <b>{fmt_date(day)}</b> встановлено як empty.\n"
            f"Розіслано сповіщень для {changed} черг."
        )
        return

    try:
        schedule = parse_schedule_text(raw)
    except ScheduleParseError:
        await message.answer("Формат: ДТЕК 29.01.2026 ...")
        return

    result = await service.apply_upload(schedule)
    if result.unchanged:
        await message.answer(
            f"Графік {result.company.title} на {fmt_date(result.day)} <b>не змінився</b>. Розсилку скасовано."
        )
        return
    await uow.commit()
    tasks.spawn(_after_save([result], notifications, update_notifier))
    await message.answer(
        f"{result.company.title} ({fmt_date(result.day)}) завантажено!\n"
        f"Розіслано сповіщень для {len(result.changed)} черг.\n\n{_summary(result)}"
    )
