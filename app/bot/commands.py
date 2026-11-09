"""Command list shown in Telegram's menu button."""

from __future__ import annotations

from aiogram import Bot
from aiogram.types import BotCommand

_COMMANDS = {
    "uk": [
        ("start", "Старт / вибір мови"), ("menu", "Головне меню"), ("sched", "Графіки"),
        ("add", "Додати чергу"), ("subs", "Мої черги"), ("compare", "Спільне світло"),
        ("settings", "Налаштування"), ("support", "Зв'язок і донат"),
    ],
    "ru": [
        ("start", "Старт / выбор языка"), ("menu", "Главное меню"), ("sched", "Графики"),
        ("add", "Добавить очередь"), ("subs", "Мои очереди"), ("compare", "Совместный свет"),
        ("settings", "Настройки"), ("support", "Связь и донат"),
    ],
}


async def set_commands(bot: Bot) -> None:
    default = [BotCommand(command=c, description=d) for c, d in _COMMANDS["uk"]]
    await bot.set_my_commands(default)
    for lang, items in _COMMANDS.items():
        await bot.set_my_commands([BotCommand(command=c, description=d) for c, d in items], language_code=lang)
