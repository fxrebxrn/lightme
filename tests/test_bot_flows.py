"""End-to-end tests: real Dispatcher + real PostgreSQL + mocked Telegram API."""

from __future__ import annotations

import sqlite3
from datetime import timedelta

import pytest
import pytest_asyncio
from aiogram.methods import (
    AnswerCallbackQuery,
    AnswerInlineQuery,
    CopyMessage,
    EditMessageText,
    SendDocument,
    SendMessage,
)

from app.bot.callbacks import (
    CmpAction,
    CmpCb,
    CompanyCb,
    LangCb,
    Mode,
    NotifyCb,
    ScheduleCb,
    SettingsCb,
    SubscribeCb,
    UnsubscribeCb,
)
from app.bot.factory import create_bot, create_container, create_dispatcher
from app.config import Settings
from app.db.engine import create_engine, create_session_factory
from app.db.uow import UnitOfWork
from app.domain.enums import Company, EventKind
from tests.helpers import callback_update, inline_update, message_update

ADMIN = 1
USER = 100


class Env:
    def __init__(self, dp, bot, session, container, factory):
        self.dp, self.bot, self.session, self.container, self.factory = dp, bot, session, container, factory

    async def send(self, update):
        self.session.clear()
        await self.dp.feed_update(self.bot, update)
        await self.container.tasks.wait()
        return self.session.requests

    async def msg(self, text, user=USER):
        return await self.send(message_update(text, user))

    async def cb(self, data, user=USER):
        if not isinstance(data, str):
            data = data.pack()
        return await self.send(callback_update(data, user))


def last_text(requests, kind=(SendMessage, EditMessageText)):
    items = [r for r in requests if isinstance(r, kind)]
    assert items, f"no {kind} in {requests}"
    return items[-1].text


def alert(requests):
    return next(r.text for r in requests if isinstance(r, AnswerCallbackQuery))


@pytest_asyncio.fixture
async def env(db_url, mocked_session, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("ADMIN_IDS", str(ADMIN))
    monkeypatch.setenv("CHANNEL_URL", "https://t.me/lightmetech")
    monkeypatch.setenv("CHANNEL_USERNAME", "lightmetech")
    monkeypatch.setenv("BOT_URL", "https://t.me/lightme_test_bot")
    monkeypatch.setenv("FLAGS_CACHE_TTL", "0")
    monkeypatch.setenv("SEND_RATE_PER_SECOND", "0")
    settings = Settings()
    engine = create_engine(settings.db)
    factory = create_session_factory(engine)
    bot = create_bot(settings, session=mocked_session)
    container = create_container(settings, bot, factory)
    from app.bot.handlers import get_routers

    for router in get_routers():
        router._parent_router = None
    dp = create_dispatcher(container)
    yield Env(dp, bot, mocked_session, container, factory)
    container.notifications.shutdown()
    await engine.dispose()


async def register(env, user=USER, lang="uk"):
    await env.msg("/start", user)
    await env.cb(LangCb(code=lang), user)


async def test_start_and_language(env):
    reqs = await env.msg("/start")
    assert "оберіть мову" in last_text(reqs)
    reqs = await env.cb(LangCb(code="ru"))
    texts = [r.text for r in reqs if hasattr(r, "text") and r.text]
    assert any("Язык установлен" in t for t in texts)
    assert any("Рекомендуем подписаться" in t for t in texts)
    reqs = await env.cb("menu:start")
    send = [r for r in reqs if isinstance(r, SendMessage)][-1]
    assert "Главное меню" in send.text
    buttons = [b.text for row in send.reply_markup.keyboard for b in row]
    assert "📅 Графики" in buttons and "⚡ Совместный свет" in buttons
    async with UnitOfWork(env.factory) as uow:
        user = await uow.users.get(USER)
        assert user.language == "ru" and user.notify_off and user.username == "tester"


async def test_subscriptions_limit_and_delete(env):
    await register(env)
    reqs = await env.msg("➕ Додати чергу")
    assert "Оберіть компанію" in last_text(reqs)
    reqs = await env.cb(CompanyCb(mode=Mode.SUB, company=Company.DTEK))
    assert "ДТЕК" in last_text(reqs)
    for q in ["1.1", "1.2", "2.1", "2.2", "3.1"]:
        assert "Підписано" in alert(await env.cb(SubscribeCb(company=Company.DTEK, queue=q)))
    assert "Ви підписані" in alert(await env.cb(SubscribeCb(company=Company.DTEK, queue="1.1")))
    assert "ліміту" in alert(await env.cb(SubscribeCb(company=Company.CEK, queue="6.2")))

    reqs = await env.msg("📁 Мої черги")
    markup = [r for r in reqs if isinstance(r, SendMessage)][-1].reply_markup
    assert len(markup.inline_keyboard) == 5
    first_id = UnsubscribeCb.unpack(markup.inline_keyboard[0][0].callback_data).id

    await register(env, user=200)
    await env.cb(UnsubscribeCb(id=first_id), user=200)
    async with UnitOfWork(env.factory) as uow:
        assert await uow.subscriptions.count_for_user(USER) == 5
    await env.cb(UnsubscribeCb(id=first_id))
    async with UnitOfWork(env.factory) as uow:
        assert await uow.subscriptions.count_for_user(USER) == 4


async def test_upload_view_and_update_notifications(env):
    await register(env)
    await env.cb(SubscribeCb(company=Company.DTEK, queue="1.1"))
    today = env.container.clock.today()
    d = today.strftime("%d.%m.%Y")

    reqs = await env.msg(f"/upload ДТЕК {d}\nЧерга 1.1\n08:00-12:00\n20:00-00:00\nЧерга 1.2\n-", user=ADMIN)
    texts = [r.text for r in reqs if isinstance(r, SendMessage)]
    admin_reply = next(t for t in texts if "завантажено" in t)
    assert "Розіслано сповіщень для 2 черг" in admin_reply
    update_msg = next(r for r in reqs if isinstance(r, SendMessage) and r.chat_id == USER)
    assert "Оновлення графіку ДТЕК 1.1" in update_msg.text
    assert "08:00 - 12:00 (4 год.)" in update_msg.text and "20:00 - 00:00 (4 год.)" in update_msg.text
    assert "Зі світлом:</b> 16 год." in update_msg.text


    reqs = await env.msg(f"/upload ДТЕК {d}\nЧерга 1.1\n08:00-12:00\n20:00-00:00\nЧерга 1.2\n-", user=ADMIN)
    assert "не змінився" in last_text(reqs)


    reqs = await env.msg(f"/upload ДТЕК {d}\nЧерга 1.1\n-")
    assert not [r for r in reqs if isinstance(r, SendMessage) and "завантажено" in (r.text or "")]

    reqs = await env.cb(ScheduleCb(company=Company.DTEK, queue="1.1", day=today.isoformat()))
    card = last_text(reqs)
    assert "Графік ДТЕК 1.1" in card and "Статус" in card and "Оновлення" in card
    assert "Без світла:</b> 8 год." in card

    reqs = await env.cb(ScheduleCb(company=Company.DTEK, queue="1.2", day=today.isoformat()))
    assert "Світло не вимикатимуть" in last_text(reqs)
    tomorrow = today + timedelta(days=1)
    reqs = await env.cb(ScheduleCb(company=Company.DTEK, queue="1.1", day=tomorrow.isoformat()))
    assert "ще не завантажено" in last_text(reqs)


    await env.msg("/avaron", user=ADMIN)
    reqs = await env.cb(ScheduleCb(company=Company.DTEK, queue="1.1", day=today.isoformat()))
    assert "аварійні відключення" in last_text(reqs)


    reqs = await env.msg(f"/upload ДТЕК/ЦЕК {d}\n-", user=ADMIN)
    assert any("встановлено як empty" in (r.text or "") for r in reqs if isinstance(r, SendMessage))
    reqs = await env.cb(ScheduleCb(company=Company.CEK, queue="6.2", day=today.isoformat()))
    assert "Світло не вимикатимуть" in last_text(reqs)


async def test_compare_flow(env):
    await register(env)
    today = env.container.clock.today().strftime("%d.%m.%Y")
    await env.msg(f"/upload ДТЕК {today}\nЧерга 1.1\n00:00-04:00\n12:00-15:00", user=ADMIN)
    await env.msg(f"/upload ЦЕК {today}\nЧерга 2.2\n03:00-06:00", user=ADMIN)

    assert "Оберіть дію" in last_text(await env.msg("⚡ Спільне світло"))
    assert "першу" in last_text(await env.cb(CmpCb(action=CmpAction.NEW)))
    await env.cb(CmpCb(action=CmpAction.COMPANY1, c1=Company.DTEK))
    assert "другу" in last_text(await env.cb(CmpCb(action=CmpAction.QUEUE1, c1=Company.DTEK, q1="1.1")))
    await env.cb(CmpCb(action=CmpAction.COMPANY2, c1=Company.DTEK, q1="1.1", c2=Company.CEK))
    pair = dict(c1=Company.DTEK, q1="1.1", c2=Company.CEK, q2="2.2")
    assert "Пара для порівняння" in last_text(await env.cb(CmpCb(action=CmpAction.QUEUE2, **pair)))
    result = last_text(await env.cb(CmpCb(action=CmpAction.RUN, day="today", **pair)))
    assert "06:00 - 12:00" in result and "15:00 - 24:00" in result
    details = last_text(await env.cb(CmpCb(action=CmpAction.DETAILS, day="today", **pair)))
    assert "00:00 - 04:00" in details and "03:00 - 06:00" in details
    no_data = last_text(await env.cb(CmpCb(action=CmpAction.RUN, day="tomorrow", **pair)))
    assert "ще не завантажено" in no_data

    for _ in range(5):
        assert "збережена" in alert(await env.cb(CmpCb(action=CmpAction.SAVE, **pair)))
    assert "ліміту" in alert(await env.cb(CmpCb(action=CmpAction.SAVE, **pair)))
    reqs = await env.cb(CmpCb(action=CmpAction.MY))
    markup = [r for r in reqs if isinstance(r, EditMessageText)][-1].reply_markup
    saved_cb = CmpCb.unpack(markup.inline_keyboard[0][0].callback_data)
    assert "06:00 - 12:00" in last_text(await env.cb(saved_cb))
    assert "видалено" in alert(await env.cb(CmpCb(action=CmpAction.DELETE, id=saved_cb.id)))
    async with UnitOfWork(env.factory) as uow:
        assert await uow.compares.count_for_user(USER) == 4


async def test_settings_and_notifications(env):
    await register(env)
    assert "Налаштування" in last_text(await env.msg("⚙️ Налаштування"))
    reqs = await env.cb(SettingsCb(action="notif"))
    edit = [r for r in reqs if isinstance(r, EditMessageText)][-1]
    labels = [row[0].text for row in edit.reply_markup.inline_keyboard]
    assert "Нагадування за 10 хв до вимкнення: ✅" in labels
    await env.cb(NotifyCb(field="notify_on_10"))
    async with UnitOfWork(env.factory) as uow:
        assert (await uow.users.get(USER)).notify_on_10 is False
    await env.cb(SettingsCb(action="all"))
    async with UnitOfWork(env.factory) as uow:
        u = await uow.users.get(USER)
        assert not any([u.notify_off, u.notify_on, u.notify_off_10, u.notify_on_10])
    await env.cb(SettingsCb(action="all"))
    async with UnitOfWork(env.factory) as uow:
        u = await uow.users.get(USER)
        assert all([u.notify_off, u.notify_on, u.notify_off_10, u.notify_on_10])
    assert "Підтримка" in last_text(await env.msg("💬 Зв`язок"))


async def test_tech_mode(env):
    await register(env)
    await env.msg("/techon", user=ADMIN)
    assert "Технічні роботи" in last_text(await env.msg("/menu"))
    assert "Головне меню" in last_text(await env.msg("/menu", user=ADMIN))
    await env.msg("/techoff", user=ADMIN)
    assert "Головне меню" in last_text(await env.msg("/menu"))


async def test_inline(env):
    today = env.container.clock.today().strftime("%d.%m.%Y")
    await env.msg(f"/upload ДТЕК {today}\nЧерга 1.1\n08:00-12:30", user=ADMIN)
    reqs = await env.send(inline_update("дтек 1.1"))
    answer = next(r for r in reqs if isinstance(r, AnswerInlineQuery))
    text = answer.results[0].input_message_content.message_text
    assert "08:00 - 12:30" in text and "Без світла:</b> 4.5 год." in text


async def test_admin_tools(env):
    await register(env)
    stats = last_text(await env.msg("/stats", user=ADMIN))
    assert "Унікальних користувачів: <code>2</code>" in stats
    reqs = await env.msg("/news Привіт!", user=ADMIN)
    assert any(isinstance(r, SendMessage) and r.chat_id == USER and r.text == "Привіт!" for r in reqs)
    assert "Розсилка завершена" in last_text(reqs)
    reqs = await env.send(message_update("/news", ADMIN, reply_to=message_update("post", ADMIN).message))
    assert any(isinstance(r, CopyMessage) for r in reqs)
    reqs = await env.msg("/getdb", user=ADMIN)
    assert any(isinstance(r, SendDocument) for r in reqs)
    reqs = await env.msg("/amenu", user=ADMIN)
    assert "Адмін меню" in last_text(reqs)


async def test_timed_notifications(env):
    await register(env)
    await env.cb(SubscribeCb(company=Company.DTEK, queue="1.1"))
    await register(env, user=200, lang="ru")
    await env.cb(SubscribeCb(company=Company.DTEK, queue="1.1"), user=200)
    await env.cb(NotifyCb(field="notify_off"), user=200)

    tomorrow = env.container.clock.tomorrow().strftime("%d.%m.%Y")
    await env.msg(f"/upload ДТЕК {tomorrow}\nЧерга 1.1\n08:00-12:00\n18:00-20:00", user=ADMIN)
    jobs = env.container.notifications.scheduler.get_jobs()
    assert len(jobs) == 8

    off_job = next(j for j in jobs if EventKind.OFF_NOW.value in j.id and "08:00" in j.id)
    env.session.clear()
    await off_job.func(**off_job.kwargs)
    sent = [r for r in env.session.requests if isinstance(r, SendMessage)]
    assert [r.chat_id for r in sent] == [USER]
    assert "ВИМКНЕНО" in sent[0].text and "Наступне ввімкнення о 12:00" in sent[0].text and "(Через 4 год.)" in sent[0].text

    on_job = next(j for j in jobs if EventKind.ON_NOW.value in j.id and "12:00" in j.id)
    env.session.clear()
    await on_job.func(**on_job.kwargs)
    sent = {r.chat_id: r.text for r in env.session.requests if isinstance(r, SendMessage)}
    assert set(sent) == {USER, 200}
    assert "Следующее отключение в 18:00" in sent[200] and "(Через 6 ч.)" in sent[200]


async def test_import_sqlite(env, tmp_path):
    path = tmp_path / "old.db"
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, company TEXT, queue TEXT);
        CREATE TABLE user_prefs (user_id INTEGER PRIMARY KEY, language TEXT DEFAULT 'uk', notify_off INTEGER DEFAULT 1,
            notify_on INTEGER DEFAULT 1, notify_off_10 INTEGER DEFAULT 1, notify_on_10 INTEGER DEFAULT 1);
        CREATE TABLE schedules (id INTEGER PRIMARY KEY AUTOINCREMENT, company TEXT, date TEXT, queue TEXT,
            off_time TEXT, on_time TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE compares (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, name TEXT,
            comp1 TEXT NOT NULL, queue1 TEXT NOT NULL, comp2 TEXT NOT NULL, queue2 TEXT NOT NULL, created_at TEXT);
        CREATE TABLE bot_settings (key TEXT PRIMARY KEY, value TEXT);
        INSERT INTO users (user_id, company, queue) VALUES (555, 'ЦЕК', '6.2'), (555, 'ДТЕК', '1.1'), (777, 'ДТЕК', '2.1');
        INSERT INTO user_prefs VALUES (555, 'ru', 1, 0, 1, 1);
        INSERT INTO schedules (company, date, queue, off_time, on_time) VALUES
            ('ДТЕК', '2026-01-29', '1.1', '08:00', '12:00'), ('ДТЕК', '2026-01-29', '1.1', '20:00', '00:00'),
            ('ДТЕК', '2026-01-29', '1.2', 'empty', 'empty');
        INSERT INTO compares (user_id, name, comp1, queue1, comp2, queue2) VALUES (555, 'x', 'ДТЕК', '1.1', 'ЦЕК', '6.2');
        INSERT INTO bot_settings VALUES ('avaron', '1');
    """)
    conn.commit()
    conn.close()

    from app.services.sqlite_import import import_sqlite

    for _ in range(2):
        async with UnitOfWork(env.factory) as uow:
            report = await import_sqlite(path, uow)
    assert report.users == 2
    async with UnitOfWork(env.factory) as uow:
        u = await uow.users.get(555)
        assert u.language == "ru" and u.notify_on is False
        assert await uow.subscriptions.total() == 3
        s = await uow.schedules.get(Company.DTEK, "1.1", __import__("datetime").date(2026, 1, 29))
        assert s.intervals == ((480, 720), (1200, 1440))
        empty = await uow.schedules.get(Company.DTEK, "1.2", __import__("datetime").date(2026, 1, 29))
        assert empty.intervals == ()
        assert await uow.compares.count_for_user(555) == 1
        assert (await uow.bot_settings.all())


async def test_import_original_db(env):
    """The real database.db from the old bot imports fine."""
    import os
    from pathlib import Path

    from app.services.sqlite_import import import_sqlite

    path = Path(os.environ.get("OLD_SQLITE_DB", "database.db"))
    if not path.exists():
        pytest.skip("no original db")
    async with UnitOfWork(env.factory) as uow:
        report = await import_sqlite(path, uow)
    assert report.users == 1 and report.subscriptions == 1


async def test_outdated_button(env):
    await register(env)
    assert "застаріла" in alert(await env.cb("vcomp_ДТЕК"))
