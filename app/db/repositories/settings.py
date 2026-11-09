from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.db.models import BotSetting
from app.db.repositories.base import Repository
from app.domain.enums import BotFlag


class BotSettingsRepository(Repository):
    async def all(self) -> dict[BotFlag, bool]:
        rows = await self.session.scalars(select(BotSetting))
        return {row.key: row.enabled for row in rows}

    async def set(self, key: BotFlag, enabled: bool) -> None:
        await self.session.execute(
            insert(BotSetting)
            .values(key=key, enabled=enabled)
            .on_conflict_do_update(index_elements=[BotSetting.key], set_={"enabled": enabled})
        )
