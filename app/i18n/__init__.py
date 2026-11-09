"""Localization.

Usage:
    i18n = Translator(defaults={"bot_url": ...})
    t = i18n.for_lang("ru")
    t("menu_main")
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.domain.enums import Language
from app.i18n import ru, uk

CATALOGS: dict[Language, dict[str, str]] = {Language.UK: uk.TEXTS, Language.RU: ru.TEXTS}


class _Defaults(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


class Texts:
    """Translator bound to one language. Call it like a function: t('key', **kwargs)."""

    __slots__ = ("lang", "_catalog", "_defaults")

    def __init__(self, lang: Language, catalog: Mapping[str, str], defaults: Mapping[str, Any]) -> None:
        self.lang = lang
        self._catalog = catalog
        self._defaults = defaults

    def __call__(self, key: str, **kwargs: Any) -> str:
        template = self._catalog.get(key) or CATALOGS[Language.UK].get(key, key)
        return template.format_map(_Defaults({**self._defaults, **kwargs}))


class Translator:
    def __init__(self, default_language: str = "uk", defaults: Mapping[str, Any] | None = None) -> None:
        self.default_language = Language.parse(default_language)
        self.defaults: dict[str, Any] = dict(defaults or {})

    def for_lang(self, lang: str | None) -> Texts:
        language = Language.parse(lang, self.default_language)
        return Texts(language, CATALOGS[language], self.defaults)

    def all_values(self, key: str) -> frozenset[str]:
        """Text of a key in every language (used to match reply-keyboard buttons)."""
        return frozenset(catalog[key] for catalog in CATALOGS.values() if key in catalog)
