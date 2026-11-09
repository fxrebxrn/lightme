from aiogram import Router

from app.bot.filters import IsAdmin
from app.bot.handlers.admin import broadcast, maintenance, upload

router = Router(name="admin")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())
router.include_routers(upload.router, broadcast.router, maintenance.router)
