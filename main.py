import asyncio
import os
import time

os.environ['TZ'] = 'Europe/Kyiv'
if hasattr(time, 'tzset'):
    time.tzset()

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config
from database.db import init_db
from handlers import admin, client
from middlewares.tech_work import TechWorkMiddleware
from services.scheduler import rebuild_jobs


async def main():
    bot = Bot(token=config.API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    scheduler = AsyncIOScheduler()

    dp.message.middleware(TechWorkMiddleware())
    dp.callback_query.middleware(TechWorkMiddleware())

    admin.register_handlers(dp, scheduler)
    client.register_handlers(dp, scheduler)

    print("🚀 System initializing...")
    init_db()
    await rebuild_jobs(bot, scheduler)
    scheduler.start()
    print("✅ Bot is ready & Scheduler started!")

    await dp.start_polling(bot, skip_updates=True)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Бот успешно остановлен!")