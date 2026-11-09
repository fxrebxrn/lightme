"""Notification about uploaded / changed schedules."""

from __future__ import annotations

import logging

from app.bot.notifications.sender import MessageSender
from app.bot.presenters.schedule import update_notification
from app.db.engine import SessionFactory
from app.db.uow import UnitOfWork
from app.i18n import Translator
from app.services.schedules import UploadResult

log = logging.getLogger(__name__)


class ScheduleUpdateNotifier:
    def __init__(self, session_factory: SessionFactory, sender: MessageSender, i18n: Translator) -> None:
        self.session_factory = session_factory
        self.sender = sender
        self.i18n = i18n

    async def notify(self, result: UploadResult) -> int:
        """Sends the new schedule of every changed queue to its subscribers."""
        total = 0
        for queue in sorted(result.changed):
            outages = result.schedule.queues[queue].outages
            async with UnitOfWork(self.session_factory) as uow:
                recipients = dict(await uow.users.recipients(result.company, queue))
            if not recipients:
                continue

            def text_for(user_id: int, _queue=queue, _outages=outages, _langs=recipients) -> str:
                t = self.i18n.for_lang(_langs[user_id])
                return update_notification(result.company, _queue, result.day, _outages, t)

            report = await self.sender.send_text(recipients.keys(), text_for)
            total += report.sent
        log.info("Schedule update %s %s: %s messages", result.company, result.day, total)
        return total
