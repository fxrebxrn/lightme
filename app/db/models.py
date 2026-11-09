"""ORM models (PostgreSQL)."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.domain.enums import BotFlag, Company

CompanyType = Enum(Company, name="company", native_enum=False, length=16, validate_strings=True)


class User(TimestampMixin, Base):
    """Telegram user + personal settings (was `user_prefs`)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    username: Mapped[str | None] = mapped_column(String(64))
    full_name: Mapped[str | None] = mapped_column(String(256))
    language: Mapped[str] = mapped_column(String(8), default="uk", server_default="uk")

    notify_off: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    notify_on: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    notify_off_10: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    notify_on_10: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())


    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())

    subscriptions: Mapped[list[Subscription]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    compares: Mapped[list[Compare]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )


class Subscription(Base):
    """User subscription to a queue (was `users`)."""

    __tablename__ = "subscriptions"
    __table_args__ = (
        UniqueConstraint("user_id", "company", "queue"),
        Index("ix_subscriptions_company_queue", "company", "queue"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    company: Mapped[Company] = mapped_column(CompanyType)
    queue: Mapped[str] = mapped_column(String(8))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="subscriptions")


class QueueSchedule(Base):
    """Schedule of one queue for one day. No outages rows == 'light all day'."""

    __tablename__ = "queue_schedules"
    __table_args__ = (
        UniqueConstraint("company", "queue", "day"),
        Index("ix_queue_schedules_day", "day"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company: Mapped[Company] = mapped_column(CompanyType)
    queue: Mapped[str] = mapped_column(String(8))
    day: Mapped[date] = mapped_column(Date)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    outages: Mapped[list[Outage]] = relationship(
        back_populates="schedule",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Outage.start_minute",
        lazy="selectin",
    )

    @property
    def intervals(self) -> tuple[tuple[int, int], ...]:
        return tuple((o.start_minute, o.end_minute) for o in self.outages)


class Outage(Base):
    """One outage interval in minutes from midnight: [start_minute, end_minute)."""

    __tablename__ = "outages"
    __table_args__ = (
        CheckConstraint(
            "start_minute >= 0 AND end_minute <= 1440 AND start_minute < end_minute",
            name="valid_interval",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    schedule_id: Mapped[int] = mapped_column(
        ForeignKey("queue_schedules.id", ondelete="CASCADE"), index=True
    )
    start_minute: Mapped[int] = mapped_column(SmallInteger)
    end_minute: Mapped[int] = mapped_column(SmallInteger)

    schedule: Mapped[QueueSchedule] = relationship(back_populates="outages")


class Compare(Base):
    """Saved pair of queues for the 'common light' feature."""

    __tablename__ = "compares"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(128))
    company1: Mapped[Company] = mapped_column(CompanyType)
    queue1: Mapped[str] = mapped_column(String(8))
    company2: Mapped[Company] = mapped_column(CompanyType)
    queue2: Mapped[str] = mapped_column(String(8))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="compares")


class BotSetting(Base):
    """Global switches: tech mode, emergency outages."""

    __tablename__ = "bot_settings"

    key: Mapped[BotFlag] = mapped_column(
        Enum(BotFlag, name="bot_flag", native_enum=False, length=32, validate_strings=True),
        primary_key=True,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
