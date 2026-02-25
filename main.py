import os
import time

# Примусове встановлення системної часової зони для всього процесу
os.environ['TZ'] = 'Europe/Kyiv'
if hasattr(time, 'tzset'):
    time.tzset()

import collections
# Милиця для сумісності
try:
    import collections.abc
    collections.Iterable = collections.abc.Iterable
except ImportError:
    pass

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config
from database.db import init_db
from services.scheduler import rebuild_jobs
from handlers import client, admin
from middlewares.tech_work import TechWorkMiddleware

# Ініціалізація
bot = Bot(token=config.API_TOKEN, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot)
scheduler = AsyncIOScheduler()

# Middlewares
dp.middleware.setup(TechWorkMiddleware())

# Реєстрація хендлерів
admin.register_handlers(dp, scheduler)
client.register_handlers(dp, scheduler)

async def on_startup(dispatcher):
    print("🚀 System initializing...")
    init_db()
    await rebuild_jobs(bot, scheduler)
    scheduler.start()
    print("✅ Bot is ready & Scheduler started!")

if __name__ == '__main__':
    executor.start_polling(dp, on_startup=on_startup, skip_updates=True, timeout=20)



