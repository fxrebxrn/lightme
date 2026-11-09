"""Application configuration.

All settings are read from environment variables (and from the `.env` file in
the project root). Settings are split into small groups so every layer only
depends on what it really needs:

    settings.bot        -> Telegram / bot behaviour
    settings.db         -> PostgreSQL connection
    settings.redis      -> optional Redis (FSM storage)
    settings.app        -> business rules (timezone, limits, reminders)
    settings.notify     -> mass-sending limits
    settings.log        -> logging
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"


def _cfg(prefix: str = "") -> SettingsConfigDict:
    return SettingsConfigDict(
        env_prefix=prefix,
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


class BotSettings(BaseSettings):
    model_config = _cfg()


    token: SecretStr = Field(validation_alias=AliasChoices("BOT_TOKEN", "API_TOKEN"))

    admin_ids_raw: str = Field(validation_alias=AliasChoices("ADMIN_IDS", "ADMIN_ID"))

    channel_username: str = Field("", validation_alias="CHANNEL_USERNAME")
    channel_url: str = Field("", validation_alias="CHANNEL_URL")
    support_username: str = Field("", validation_alias="SUPPORT_USERNAME")
    donate_url: str = Field("", validation_alias="DONATE_URL")

    skip_updates: bool = Field(True, validation_alias="BOT_SKIP_UPDATES")

    @property
    def admin_ids(self) -> frozenset[int]:
        ids = set()
        for part in self.admin_ids_raw.replace(";", ",").split(","):
            part = part.strip()
            if part:
                ids.add(int(part))
        return frozenset(ids)

    @field_validator("admin_ids_raw", mode="before")
    @classmethod
    def _admins_to_str(cls, v):
        return str(v)

    @property
    def channel_mention(self) -> str:
        name = self.channel_username.strip()
        if not name:
            return ""
        return name if name.startswith("@") else f"@{name}"


class DatabaseSettings(BaseSettings):
    model_config = _cfg("POSTGRES_")



    url: str | None = Field(None, validation_alias=AliasChoices("DATABASE_URL", "POSTGRES_URL"))

    host: str = "localhost"
    port: int = 5432
    user: str = "lightme"
    password: SecretStr = SecretStr("lightme")
    db: str = "lightme"

    echo: bool = Field(False, validation_alias="DB_ECHO")
    pool_size: int = Field(10, validation_alias="DB_POOL_SIZE")
    max_overflow: int = Field(20, validation_alias="DB_MAX_OVERFLOW")
    auto_migrate: bool = Field(True, validation_alias="DB_AUTO_MIGRATE")

    @property
    def dsn(self) -> str:
        if self.url:
            url = self.url
            for prefix in ("postgres://", "postgresql://"):
                if url.startswith(prefix):
                    return "postgresql+asyncpg://" + url[len(prefix):]
            return url
        pwd = self.password.get_secret_value()
        return f"postgresql+asyncpg://{self.user}:{pwd}@{self.host}:{self.port}/{self.db}"


class RedisSettings(BaseSettings):
    model_config = _cfg()



    url: str | None = Field(None, validation_alias="REDIS_URL")


class AppSettings(BaseSettings):
    model_config = _cfg()

    timezone: str = Field("Europe/Kyiv", validation_alias="TIMEZONE")
    default_language: str = Field("uk", validation_alias="DEFAULT_LANGUAGE")
    max_subscriptions: int = Field(5, validation_alias="MAX_SUBSCRIPTIONS")
    max_compares: int = Field(5, validation_alias="MAX_COMPARES")
    reminder_minutes: int = Field(10, validation_alias="REMINDER_MINUTES")

    bot_url: str = Field("", validation_alias="BOT_URL")

    flags_cache_ttl: float = Field(5.0, validation_alias="FLAGS_CACHE_TTL")

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)


class NotifySettings(BaseSettings):
    model_config = _cfg()


    rate_per_second: float = Field(25, validation_alias="SEND_RATE_PER_SECOND")
    max_retries: int = Field(3, validation_alias="SEND_MAX_RETRIES")


class LogSettings(BaseSettings):
    model_config = _cfg()

    level: str = Field("INFO", validation_alias="LOG_LEVEL")


class Settings(BaseSettings):
    model_config = _cfg()

    bot: BotSettings = Field(default_factory=BotSettings)
    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    app: AppSettings = Field(default_factory=AppSettings)
    notify: NotifySettings = Field(default_factory=NotifySettings)
    log: LogSettings = Field(default_factory=LogSettings)


@lru_cache
def get_settings() -> Settings:
    return Settings()
