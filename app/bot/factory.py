"""Builds Bot and Dispatcher and wires all dependencies (composition root)."""

from __future__ import annotations

from dataclasses import dataclass

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.base import BaseStorage
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.handlers import get_routers
from app.bot.middlewares import DbSessionMiddleware, TechModeMiddleware, UserMiddleware
from app.bot.notifications.scheduler import NotificationScheduler
from app.bot.notifications.sender import MessageSender
from app.bot.notifications.updates import ScheduleUpdateNotifier
from app.bot.tasks import BackgroundTasks
from app.config import Settings
from app.core.clock import Clock
from app.db.engine import SessionFactory
from app.i18n import Translator
from app.services.flags import FlagsService


@dataclass
class Container:
    """Everything the bot needs at runtime. Handlers receive these by name."""

    settings: Settings
    session_factory: SessionFactory
    clock: Clock
    i18n: Translator
    flags: FlagsService
    sender: MessageSender
    notifications: NotificationScheduler
    update_notifier: ScheduleUpdateNotifier
    tasks: BackgroundTasks

    def as_workflow_data(self) -> dict:
        return {
            "settings": self.settings,
            "admin_ids": self.settings.bot.admin_ids,
            "clock": self.clock,
            "i18n": self.i18n,
            "flags": self.flags,
            "sender": self.sender,
            "notifications": self.notifications,
            "update_notifier": self.update_notifier,
            "tasks": self.tasks,
        }


def create_bot(settings: Settings, **kwargs) -> Bot:
    return Bot(
        token=settings.bot.token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        **kwargs,
    )


def create_storage(settings: Settings) -> BaseStorage:
    if settings.redis.url:
        from aiogram.fsm.storage.redis import RedisStorage

        return RedisStorage.from_url(settings.redis.url)
    return MemoryStorage()


def create_container(settings: Settings, bot: Bot, session_factory: SessionFactory) -> Container:
    clock = Clock(settings.app.tz)
    i18n = Translator(
        settings.app.default_language,
        defaults={
            "channel": settings.bot.channel_mention,
            "channel_url": settings.bot.channel_url,
            "bot_url": settings.app.bot_url,
            "minutes": settings.app.reminder_minutes,
        },
    )
    sender = MessageSender(bot, session_factory, settings.notify.rate_per_second, settings.notify.max_retries)
    return Container(
        settings=settings,
        session_factory=session_factory,
        clock=clock,
        i18n=i18n,
        flags=FlagsService(session_factory, settings.app.flags_cache_ttl),
        sender=sender,
        notifications=NotificationScheduler(session_factory, sender, i18n, clock, settings.app.reminder_minutes),
        update_notifier=ScheduleUpdateNotifier(session_factory, sender, i18n),
        tasks=BackgroundTasks(),
    )


def create_dispatcher(container: Container) -> Dispatcher:
    dp = Dispatcher(storage=create_storage(container.settings), **container.as_workflow_data())


    dp.update.outer_middleware(DbSessionMiddleware(container.session_factory))
    dp.update.outer_middleware(UserMiddleware())

    dp.message.outer_middleware(TechModeMiddleware())
    dp.callback_query.outer_middleware(TechModeMiddleware())

    dp.include_routers(*get_routers())
    return dp
