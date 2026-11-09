"""Timed notifications: planning (APScheduler jobs) and delivery."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.bot.notifications.sender import MessageSender
from app.bot.presenters.events import event_text
from app.core.clock import Clock
from app.db.engine import SessionFactory
from app.db.uow import UnitOfWork
from app.domain.enums import Company, EventKind
from app.domain.planner import NotificationPlanner, PlannedEvent
from app.i18n import Translator
from app.services.schedules import ScheduleService

log = logging.getLogger(__name__)

JOB_PREFIX = "event:"


class NotificationScheduler:
    """Keeps APScheduler jobs in sync with the uploaded schedules.

    One job per (queue, event) - recipients and their preferences are read at
    send time, so subscribing / changing settings never requires a rebuild.
    """

    def __init__(self, session_factory: SessionFactory, sender: MessageSender, i18n: Translator,
                 clock: Clock, reminder_minutes: int) -> None:
        self.session_factory = session_factory
        self.sender = sender
        self.i18n = i18n
        self.clock = clock
        self.reminder_minutes = reminder_minutes
        self.planner = NotificationPlanner(clock.tz, reminder_minutes)
        self.scheduler = AsyncIOScheduler(
            timezone=clock.tz,
            job_defaults={"misfire_grace_time": 120, "coalesce": True, "max_instances": 1},
        )
        self._lock = asyncio.Lock()

    def start(self) -> None:
        self.scheduler.start()

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    async def rebuild(self) -> int:
        """Re-plans all future notifications. Returns number of scheduled jobs."""
        async with self._lock:
            async with UnitOfWork(self.session_factory) as uow:
                index = await ScheduleService(uow).build_index(self.clock.today())
            events = self.planner.plan(index, self.clock.now())

            for job in self.scheduler.get_jobs():
                if job.id.startswith(JOB_PREFIX):
                    job.remove()
            for event in events:
                self.scheduler.add_job(
                    self.fire,
                    trigger="date",
                    run_date=event.run_at,
                    id=JOB_PREFIX + event.job_id,
                    replace_existing=True,
                    kwargs={
                        "company": event.company.value,
                        "queue": event.queue,
                        "kind": event.kind.value,
                        "event_at": event.event_at,
                        "next_at": event.next_at,
                    },
                )
            log.info("Notification jobs rebuilt: %s", len(events))
            return len(events)

    async def fire(self, company: str, queue: str, kind: str, event_at: datetime, next_at: datetime | None) -> None:
        event = PlannedEvent(Company(company), queue, EventKind(kind), event_at, event_at, next_at)
        async with UnitOfWork(self.session_factory) as uow:
            recipients = await uow.users.recipients(event.company, queue, event.kind.pref_field)
        if not recipients:
            return
        langs = dict(recipients)

        def text_for(user_id: int) -> str:
            t = self.i18n.for_lang(langs[user_id])
            return event_text(event.kind, event.company, queue, self.clock.localize(event_at),
                              self.clock.localize(next_at) if next_at else None, self.reminder_minutes, t)

        report = await self.sender.send_text(langs.keys(), text_for)
        log.info("%s %s %s: sent=%s failed=%s", company, queue, kind, report.sent, report.failed)
