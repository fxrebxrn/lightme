"""Rate-limited mass sending with Telegram error handling."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass, field

from aiogram import Bot
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNetworkError,
    TelegramRetryAfter,
)

from app.db.engine import SessionFactory
from app.db.uow import UnitOfWork

log = logging.getLogger(__name__)

SendFn = Callable[[int], Awaitable[object]]


@dataclass
class SendReport:
    sent: int = 0
    failed: int = 0
    blocked: list[int] = field(default_factory=list)


class RateLimiter:
    """Simple async limiter: at most `rate` calls per second (evenly spaced)."""

    def __init__(self, rate: float) -> None:
        self.interval = 1.0 / rate if rate > 0 else 0.0
        self._lock = asyncio.Lock()
        self._next = 0.0

    async def wait(self) -> None:
        if not self.interval:
            return
        async with self._lock:
            now = time.monotonic()
            delay = self._next - now
            self._next = max(now, self._next) + self.interval
        if delay > 0:
            await asyncio.sleep(delay)


class MessageSender:
    def __init__(self, bot: Bot, session_factory: SessionFactory, rate_per_second: float, max_retries: int) -> None:
        self.bot = bot
        self.session_factory = session_factory
        self.limiter = RateLimiter(rate_per_second)
        self.max_retries = max_retries

    async def send_text(self, chat_ids: Iterable[int], text_for: Callable[[int], str]) -> SendReport:
        async def send(chat_id: int):
            return await self.bot.send_message(chat_id, text_for(chat_id), disable_web_page_preview=True)

        return await self.run(chat_ids, send)

    async def run(self, chat_ids: Iterable[int], send: SendFn) -> SendReport:
        report = SendReport()
        for chat_id in chat_ids:
            result = await self._send_one(chat_id, send)
            if result == "ok":
                report.sent += 1
            else:
                report.failed += 1
                if result == "blocked":
                    report.blocked.append(chat_id)
        if report.blocked:
            async with UnitOfWork(self.session_factory) as uow:
                await uow.users.deactivate(report.blocked)
        return report

    async def _send_one(self, chat_id: int, send: SendFn) -> str:
        for attempt in range(self.max_retries + 1):
            await self.limiter.wait()
            try:
                await send(chat_id)
                return "ok"
            except TelegramRetryAfter as e:
                log.warning("Flood control, sleeping %ss", e.retry_after)
                await asyncio.sleep(e.retry_after + 0.5)
            except TelegramForbiddenError:
                return "blocked"
            except TelegramBadRequest as e:
                message = str(e).lower()
                if "chat not found" in message or "user is deactivated" in message:
                    return "blocked"
                log.warning("Bad request for %s: %s", chat_id, e)
                return "error"
            except TelegramNetworkError as e:
                log.warning("Network error for %s (attempt %s): %s", chat_id, attempt + 1, e)
                await asyncio.sleep(1 + attempt)
            except Exception:
                log.exception("Unexpected error while sending to %s", chat_id)
                return "error"
        return "error"
