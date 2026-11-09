"""Admin service commands: help, menu, stats, flags, DB export/import."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import FSInputFile, Message

from app.bot.keyboards.admin import admin_menu
from app.bot.notifications.scheduler import NotificationScheduler
from app.config import Settings
from app.core.clock import Clock
from app.db.uow import UnitOfWork
from app.domain.enums import BotFlag
from app.services.export import export_json, export_pg_dump
from app.services.flags import FlagsService
from app.services.sqlite_import import import_sqlite
from app.services.stats import collect_stats

router = Router(name="admin.maintenance")
log = logging.getLogger(__name__)

HELP = (
    "<b>ADMIN CMD:</b>\n\n"
    "/ahelp - Це меню\n"
    "/amenu - Адмін-меню з кнопками\n"
    "/stats - Статистика бота\n"
    "/upload КОМПАНІЯ ДАТА - Завантажити графік\n"
    "/news - Розсилка всім користувачам\n"
    "/getdb - Вивантажити базу даних\n"
    "/importdb - (підпис до .db файлу) Імпорт старої SQLite бази\n"
    "/techon - Тех. роботи ВКЛ\n"
    "/techoff - Тех. роботи ВИКЛ\n"
    "/avaron - Аварійні відключення ВКЛ\n"
    "/avaroff - Аварійні відключення ВИКЛ\n"
)


@router.message(Command("ahelp"))
async def admin_help(message: Message) -> None:
    await message.answer(HELP)


@router.message(Command("amenu"))
async def menu(message: Message, clock: Clock) -> None:
    await message.answer("Адмін меню:", reply_markup=admin_menu(clock.today()))


@router.message(Command("stats"))
async def stats(message: Message, uow: UnitOfWork) -> None:
    s = await collect_stats(uow)
    await message.answer(
        "📊 <b>Статистика бота:</b>\n\n"
        f"👤 Унікальних користувачів: <code>{s.users}</code>\n"
        f"🔔 Активних підписок на черги: <code>{s.subscriptions}</code>\n"
        f"🚫 Заблокували бота: <code>{s.blocked}</code>"
    )


_FLAG_COMMANDS = {
    "techon": (BotFlag.TECH_MODE, True, "TECH MODE: ON"),
    "techoff": (BotFlag.TECH_MODE, False, "TECH MODE: OFF"),
    "avaron": (BotFlag.EMERGENCY, True, "Режим Аварійних відключень: УВІМКНЕНО"),
    "avaroff": (BotFlag.EMERGENCY, False, "Режим Аварійних відключень: ВИМКНЕНО"),
}


@router.message(Command(*_FLAG_COMMANDS))
async def set_flag(message: Message, flags: FlagsService) -> None:
    command = message.text.split()[0].lstrip("/").split("@")[0].lower()
    flag, enabled, answer = _FLAG_COMMANDS[command]
    await flags.set(flag, enabled)
    await message.answer(answer)


@router.message(Command("getdb"))
async def get_db(message: Message, uow: UnitOfWork, settings: Settings) -> None:
    try:
        path = await export_pg_dump(settings.db.dsn)
        caption = "База даних (pg_dump, SQL)"
    except Exception as e:
        log.warning("pg_dump failed: %s", e)
        path = None
    if path is None:
        path = await export_json(uow)
        caption = "База даних (JSON)"
    try:
        await message.answer_document(FSInputFile(path, filename=path.name), caption=caption)
    finally:
        path.unlink(missing_ok=True)


@router.message(Command("importdb"), F.document)
async def import_db(message: Message, bot: Bot, uow: UnitOfWork, notifications: NotificationScheduler) -> None:
    """Send the old database.db with caption /importdb -> data is merged into PostgreSQL."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "import.db"
        await bot.download(message.document, destination=path)
        try:
            report = await import_sqlite(path, uow)
        except Exception as e:
            await message.answer(f"Не вдалося імпортувати базу: <code>{e}</code>")
            return
    await uow.commit()
    await notifications.rebuild()
    await message.answer(f"✅ Імпорт завершено.\n<code>{report}</code>")


@router.message(Command("importdb"))
async def import_db_help(message: Message) -> None:
    await message.answer("Надішліть файл старої бази <code>database.db</code> з підписом <code>/importdb</code>.")
