from aiogram import BaseMiddleware, types
from config import settings
from database.db import get_tech_mode
from locales.strings import get_text

class TechWorkMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        from_user = getattr(event, "from_user", None)
        if from_user and from_user.id == settings.ADMIN_ID:
            return await handler(event, data)
        if get_tech_mode():
            if isinstance(event, types.Message):
                await event.answer(get_text('uk', 'tech_work'))
            elif isinstance(event, types.CallbackQuery):
                await event.answer(get_text('uk', 'tech_work'), show_alert=True)
            return None

        return await handler(event, data)