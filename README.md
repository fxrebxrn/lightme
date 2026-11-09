# LightMe Telegram Bot v2

Telegram-бот для мониторинга графиков отключений электроэнергии (ДТЕК/ЦЕК), подписок на очереди, сравнения двух очередей и автоматических уведомлений.

## Что умеет бот

- Показывает графики по компаниям **ДТЕК** и **ЦЕК** (сегодня / завтра, статус «свет есть до…», статистика).
- Сохранение до 5 очередей на пользователя (`MAX_SUBSCRIPTIONS`).
- 4 типа уведомлений: отключение, включение, напоминание за 10 минут до отключения и до включения (`REMINDER_MINUTES`).
- Уведомление подписчикам, когда админ загружает изменённый график.
- Сравнение 2 очередей — интервалы «совместного света», до 5 сохранённых пар (`MAX_COMPARES`).
- Inline-режим: `@bot ДТЕК 1.1 завтра`.
- 2 языка интерфейса: **українська** и **русский**.
- Админ-команды: загрузка графиков, рассылки, техработы, аварийный режим, статистика, выгрузка/импорт БД.

## Технологии

- **Python 3.11+** (рекомендуется 3.12)
- **aiogram 3.26**: роутеры, `CallbackData`-фабрики, middlewares, DI через workflow data
- **PostgreSQL 16** + **SQLAlchemy 2 (async ORM)** + **asyncpg**
- **Alembic** для миграций схемы
- **pydantic-settings** для конфига
- **APScheduler** для запланированных уведомлений
- **zoneinfo** (вместо pytz)
- **pytest** (тесты на настоящем PostgreSQL), **ruff** (линтер)

## Архитектура

Слои зависят только «вниз»: `bot → services → db / domain`. Бизнес-логика не знает про Telegram,
поэтому её можно переиспользовать в Telegram Mini App / HTTP API без изменений.

```text
app/
├── __main__.py              # Точка входа: python -m app
├── cli.py                   # migrate / import-sqlite
├── config.py                # Все настройки (pydantic-settings), сгруппированы по разделам
├── core/                    # Clock (время в Europe/Kyiv), логирование
├── domain/                  # Чистая логика без БД и Telegram
│   ├── enums.py             #   Company, Language, EventKind, BotFlag
│   ├── schedule.py          #   Парсер /upload
│   ├── intervals.py         #   Математика интервалов (совместный свет)
│   ├── planner.py           #   Планировщик событий-уведомлений
│   └── timeutils.py
├── db/                      # Слой данных
│   ├── models.py            #   ORM-модели
│   ├── repositories/        #   Запросы к БД (по одному репозиторию на сущность)
│   ├── uow.py               #   Unit of Work: одна транзакция на апдейт
│   ├── engine.py, migrate.py
├── services/                # Сценарии использования (подписки, графики, сравнение, флаги, импорт/экспорт)
├── i18n/                    # Тексты uk/ru + Translator
└── bot/                     # Всё, что связано с Telegram
    ├── factory.py           #   Сборка Bot/Dispatcher и зависимостей (composition root)
    ├── callbacks.py         #   Типизированные callback data
    ├── filters.py           #   IsAdmin, TextButton
    ├── middlewares/         #   DB-сессия, пользователь+язык, техработы
    ├── keyboards/           #   Клавиатуры
    ├── presenters/          #   Формирование текстов сообщений
    ├── notifications/       #   APScheduler-задачи, рассылка с rate limit
    └── handlers/            #   user/* и admin/* роутеры
migrations/                  # Alembic
tests/                       # Юнит- и e2e-тесты
```

### База данных (PostgreSQL)

| Таблица | Что хранит |
|---|---|
| `users` | Telegram-пользователь: язык, 4 флага уведомлений, `is_active` (не заблокировал ли бота) |
| `subscriptions` | Подписки пользователя на очереди (`UNIQUE user+company+queue`) |
| `queue_schedules` | График одной очереди на один день + время последнего обновления |
| `outages` | Интервалы отключений (минуты от полуночи, `00:00` в конце = `1440`) |
| `compares` | Сохранённые пары для «Спільне світло» |
| `bot_settings` | Флаги `TECH_MODE` и `EMERGENCY` |

Нет строк в `outages` у графика → «світло не вимикатимуть». Нет `queue_schedules` → «графік ще не завантажено».

## Быстрый старт

### Вариант А: Docker (бот + PostgreSQL одной командой)

```bash
cp .env.example .env      # заполните BOT_TOKEN, ADMIN_IDS и т.д.
docker compose up -d --build
docker compose logs -f bot
```

### Вариант Б: локально

```bash
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env               # заполните переменные и параметры PostgreSQL
python -m app
```

Миграции применяются автоматически при старте (`DB_AUTO_MIGRATE=true`). Вручную: `python -m app.cli migrate`.

### Railway

1. Добавьте плагин PostgreSQL — Railway сам выставит `DATABASE_URL` (формат `postgres://` поддерживается).
2. Добавьте переменные из `.env.example`.
3. Start command: `python -m app` (или используйте Dockerfile).

## Перенос данных со старой SQLite-базы

```bash
python -m app.cli import-sqlite /path/to/database.db
```

Или отправьте `database.db` боту файлом с подписью `/importdb` (только админ).
Переносятся пользователи с языком и настройками уведомлений, подписки, графики, сохранённые сравнения и флаги.
Импорт идемпотентный: повторный запуск не создаёт дублей.

## Переменные окружения

| Переменная | Обязательна | По умолчанию | Описание |
|---|---|---|---|
| `BOT_TOKEN` (или `API_TOKEN`) | ✅ | — | Токен от @BotFather |
| `ADMIN_IDS` (или `ADMIN_ID`) | ✅ | — | ID админов через запятую |
| `CHANNEL_USERNAME` | | — | @канал бота (сообщение о техработах) |
| `CHANNEL_URL` | | — | Ссылка на канал (кнопка «Підписатись», текст поддержки) |
| `SUPPORT_USERNAME` | | — | Контакт поддержки |
| `DONATE_URL` | | — | Ссылка на донат |
| `BOT_URL` | | авто | Ссылка «Монітор світла»; пусто — берётся username бота |
| `DATABASE_URL` | ✅* | — | Полный URL PostgreSQL |
| `POSTGRES_HOST/PORT/USER/PASSWORD/DB` | ✅* | localhost/5432/lightme/lightme/lightme | Если нет `DATABASE_URL` |
| `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_ECHO` | | 10, 20, false | Пул соединений, лог SQL |
| `DB_AUTO_MIGRATE` | | true | Применять миграции при старте |
| `REDIS_URL` | | — | FSM в Redis (для нескольких реплик) |
| `TIMEZONE` | | Europe/Kyiv | Часовой пояс |
| `DEFAULT_LANGUAGE` | | uk | Язык по умолчанию |
| `MAX_SUBSCRIPTIONS` / `MAX_COMPARES` | | 5 / 5 | Лимиты |
| `REMINDER_MINUTES` | | 10 | За сколько минут напоминать |
| `SEND_RATE_PER_SECOND` / `SEND_MAX_RETRIES` | | 25 / 3 | Лимиты рассылок |
| `BOT_SKIP_UPDATES` | | true | Пропускать апдейты, пришедшие пока бот был выключен |
| `LOG_LEVEL` | | INFO | Уровень логов |

\* нужен либо `DATABASE_URL`, либо `POSTGRES_*`.

## Пользовательские команды

`/start`, `/menu`, `/sched`, `/add`, `/subs`, `/compare`, `/settings`, `/support`, `/check` (время сервера).
Основная навигация — кнопками.

## Админ-команды

| Команда | Действие |
|---|---|
| `/ahelp` | Справка |
| `/amenu` | Админ-меню с кнопками |
| `/upload ...` | Загрузка графика |
| `/news текст` или reply на пост + `/news` | Рассылка (копирует пост с премиум-эмодзи/фото) |
| `/stats` | Пользователи, подписки, кто заблокировал бота |
| `/getdb` | Выгрузка БД (`pg_dump`, если установлен, иначе JSON) |
| `/importdb` | Подпись к файлу `database.db` — импорт старой базы |
| `/techon` / `/techoff` | Режим техработ |
| `/avaron` / `/avaroff` | Предупреждение об аварийных отключениях |

### Формат `/upload`

```text
/upload ДТЕК 29.01.2026
Черга 1.1
00:00-04:00
12:00-15:00
Черга 1.2
-
```

Загрузка заменяет весь график компании на дату. Подписчики получают уведомление только по очередям, которые изменились.

Все очереди без отключений:

```text
/upload ДТЕК/ЦЕК 29.01.2026
-
```

(или одной строкой `/upload ДТЕК 29.01.2026 -` — так работают кнопки `/amenu`).

## Разработка

```bash
pip install -r requirements-dev.txt
ruff check app tests
TEST_DATABASE_URL=postgresql+asyncpg://lightme:lightme@localhost:5432/lightme_test pytest
```

Новая миграция после изменения моделей:

```bash
alembic revision --autogenerate -m "describe change"
```

### Как добавить…

- **новую компанию** — добавить значение в `Company` (`app/domain/enums.py`), миграция не нужна;
- **новый язык** — файл в `app/i18n/` + значение в `Language`;
- **Telegram Mini App / API** — новый пакет (например, `app/api/` на FastAPI), который использует те же `services/` и `UnitOfWork`; бот менять не нужно.
