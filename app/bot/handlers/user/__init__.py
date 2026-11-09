from aiogram import Router

from app.bot.handlers.user import compare, fallback, inline, schedules, settings, start, subscriptions, support

router = Router(name="user")
router.include_routers(
    start.router,
    compare.router,
    schedules.router,
    subscriptions.router,
    settings.router,
    support.router,
    inline.router,
    fallback.router,
)
