"""Entry point: `python -m app`."""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot

from app.bot.commands import set_commands
from app.bot.factory import create_bot, create_container, create_dispatcher
from app.config import get_settings
from app.core.logging import setup_logging
from app.db.engine import create_engine, create_session_factory
from app.db.migrate import upgrade_head_async

log = logging.getLogger("app")


async def main() -> None:
    settings = get_settings()
    setup_logging(settings.log.level)

    if settings.db.auto_migrate:
        log.info("Applying database migrations...")
        await upgrade_head_async()

    engine = create_engine(settings.db)
    session_factory = create_session_factory(engine)
    bot: Bot = create_bot(settings)
    container = create_container(settings, bot, session_factory)
    dp = create_dispatcher(container)

    if not settings.app.bot_url:
        me = await bot.get_me()
        container.i18n.defaults["bot_url"] = f"https://t.me/{me.username}"

    try:
        await set_commands(bot)
    except Exception:
        log.warning("Could not set bot commands", exc_info=True)

    await container.notifications.rebuild()
    container.notifications.start()
    log.info("Bot started")
    try:
        await dp.start_polling(bot, drop_pending_updates=settings.bot.skip_updates)
    finally:
        container.notifications.shutdown()
        await container.tasks.wait()
        await bot.session.close()
        await engine.dispose()
        log.info("Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
