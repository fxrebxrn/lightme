"""/news - broadcast to all users."""

from __future__ import annotations

from aiogram import Bot, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from app.bot.notifications.sender import MessageSender
from app.bot.tasks import BackgroundTasks
from app.db.uow import UnitOfWork

router = Router(name="admin.broadcast")

HELP = (
    "ℹ <b>Як зробити розсилку:</b>\n\n"
    "1. <b>З Преміум емодзі/фото:</b> Напишіть пост у цей чат, натисніть на нього 'Відповісти' (Reply) "
    "і напишіть <code>/news</code>.\n"
    "2. <b>Тільки текст:</b> Напишіть <code>/news Ваш текст</code>"
)


@router.message(Command("news"))
async def news(message: Message, command: CommandObject, bot: Bot, uow: UnitOfWork, sender: MessageSender,
               tasks: BackgroundTasks) -> None:
    source = message.reply_to_message
    text = (command.args or "").strip()
    if not source and not text:
        await message.answer(HELP)
        return

    user_ids = await uow.users.active_ids()
    if not user_ids:
        await message.answer("Немає користувачів для розсилки.")
        return
    status = await message.answer(f"⏳ Починаю розсилку на {len(user_ids)} користувачів...")

    if source:
        async def send(chat_id: int):
            return await bot.copy_message(chat_id=chat_id, from_chat_id=message.chat.id, message_id=source.message_id)
    else:
        async def send(chat_id: int):
            return await bot.send_message(chat_id, text)

    async def run() -> None:
        report = await sender.run(user_ids, send)
        await bot.edit_message_text(
            chat_id=status.chat.id, message_id=status.message_id, text="<b>Розсилка завершена!</b>\n\n"
            f"Отримали: <code>{report.sent}</code>\n"
            f"Не вдалося (заблокували бота): <code>{report.failed}</code>",
        )

    tasks.spawn(run())
