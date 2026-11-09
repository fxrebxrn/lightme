from __future__ import annotations

from enum import StrEnum


class Company(StrEnum):
    """Energy companies. The value is the stable code stored in DB and callback data."""

    DTEK = "DTEK"
    CEK = "CEK"

    @property
    def title(self) -> str:
        return _COMPANY_TITLES[self]

    @classmethod
    def parse(cls, raw: str) -> Company | None:
        """Accepts code ('DTEK') or human title ('ДТЕК', 'ЦЕК', 'dtek')."""
        if not raw:
            return None
        value = raw.strip().upper()
        for company, aliases in _COMPANY_ALIASES.items():
            if value in aliases:
                return company
        return None


_COMPANY_TITLES = {Company.DTEK: "ДТЕК", Company.CEK: "ЦЕК"}
_COMPANY_ALIASES = {
    Company.DTEK: {"DTEK", "ДТЕК"},
    Company.CEK: {"CEK", "ЦЕК", "CEC"},
}


class Language(StrEnum):
    UK = "uk"
    RU = "ru"

    @classmethod
    def parse(cls, raw: str | None, default: Language = None) -> Language:
        try:
            return cls(raw)
        except ValueError:
            return default or cls.UK


class EventKind(StrEnum):
    """Kinds of scheduled notifications (4 types from README)."""

    OFF_NOW = "off_now"
    ON_NOW = "on_now"
    OFF_REMINDER = "off_reminder"
    ON_REMINDER = "on_reminder"

    @property
    def pref_field(self) -> str:
        """User preference column that enables this notification kind."""
        return _PREF_FIELDS[self]


_PREF_FIELDS = {
    EventKind.OFF_NOW: "notify_off",
    EventKind.ON_NOW: "notify_on",
    EventKind.OFF_REMINDER: "notify_off_10",
    EventKind.ON_REMINDER: "notify_on_10",
}

NOTIFY_FIELDS: tuple[str, ...] = ("notify_off", "notify_on", "notify_off_10", "notify_on_10")


class BotFlag(StrEnum):
    TECH_MODE = "tech_mode"
    EMERGENCY = "emergency"
