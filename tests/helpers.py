from __future__ import annotations

from datetime import UTC, datetime
from itertools import count

from aiogram.types import CallbackQuery, Chat, InlineQuery, Message, Update, User

_ids = count(1)


def tg_user(user_id: int = 100, username: str = "tester") -> User:
    return User(id=user_id, is_bot=False, first_name="Test", username=username, language_code="uk")


def message_update(text: str, user_id: int = 100, reply_to: Message | None = None) -> Update:
    msg = Message(
        message_id=next(_ids), date=datetime.now(UTC), chat=Chat(id=user_id, type="private"),
        from_user=tg_user(user_id), text=text, reply_to_message=reply_to,
    )
    return Update(update_id=next(_ids), message=msg)


def callback_update(data: str, user_id: int = 100) -> Update:
    msg = Message(message_id=next(_ids), date=datetime.now(UTC), chat=Chat(id=user_id, type="private"),
                  from_user=User(id=42, is_bot=True, first_name="bot"), text="old")
    cb = CallbackQuery(id=str(next(_ids)), from_user=tg_user(user_id), chat_instance="ci", message=msg, data=data)
    return Update(update_id=next(_ids), callback_query=cb)


def inline_update(query: str, user_id: int = 100) -> Update:
    iq = InlineQuery(id=str(next(_ids)), from_user=tg_user(user_id), query=query, offset="")
    return Update(update_id=next(_ids), inline_query=iq)
