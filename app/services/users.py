from __future__ import annotations

from app.db.models import User
from app.db.uow import UnitOfWork
from app.domain.enums import NOTIFY_FIELDS, Language


class UserSettingsService:
    """Language and notification preferences."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def set_language(self, user: User, lang: Language) -> None:
        user.language = lang.value

    async def toggle(self, user: User, field: str) -> bool:
        if field not in NOTIFY_FIELDS:
            raise ValueError(f"Unknown notification setting: {field}")
        value = not getattr(user, field)
        setattr(user, field, value)
        return value

    async def toggle_all(self, user: User) -> bool:
        """If anything is enabled -> disable all, otherwise enable all."""
        new_value = not any(getattr(user, f) for f in NOTIFY_FIELDS)
        for field in NOTIFY_FIELDS:
            setattr(user, field, new_value)
        return new_value
