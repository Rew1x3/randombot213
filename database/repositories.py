from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Sequence, Tuple

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Giveaway, Participant, Winner


class GiveawayRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_giveaway(
        self,
        *,
        title: str,
        prizes_text: str,
        winners_count: int,
        subscription_channel_id: int,
        conditions_text: Optional[str],
        end_time: datetime,
        publish_chat_id: int,
        created_by: Optional[int],
    ) -> Giveaway:
        giveaway = Giveaway(
            title=title,
            prizes_text=prizes_text,
            winners_count=winners_count,
            subscription_channel_id=subscription_channel_id,
            conditions_text=conditions_text,
            end_time=end_time,
            publish_chat_id=publish_chat_id,
            created_by=created_by,
        )
        self.session.add(giveaway)
        await self.session.commit()
        await self.session.refresh(giveaway)
        return giveaway

    async def get_giveaway(self, giveaway_id: int) -> Optional[Giveaway]:
        res = await self.session.execute(select(Giveaway).where(Giveaway.id == giveaway_id))
        return res.scalar_one_or_none()

    async def get_due_giveaways(self, now: datetime, limit: int = 20) -> List[int]:
        res = await self.session.execute(
            select(Giveaway.id).where(Giveaway.status == "active", Giveaway.end_time <= now).order_by(Giveaway.end_time).limit(limit)
        )
        return list(res.scalars().all())

    async def get_active_giveaways(self, *, limit: int = 20) -> List[Giveaway]:
        res = await self.session.execute(
            select(Giveaway).where(Giveaway.status == "active").order_by(Giveaway.end_time).limit(limit)
        )
        return list(res.scalars().all())

    async def add_participant(self, giveaway_id: int, telegram_id: int) -> bool:
        # Проверяем заранее, чтобы не ловить ошибки уникальности в каждом случае
        res = await self.session.execute(
            select(Participant.id).where(Participant.giveaway_id == giveaway_id, Participant.telegram_id == telegram_id)
        )
        exists = res.scalar_one_or_none()
        if exists is not None:
            return False

        participant = Participant(giveaway_id=giveaway_id, telegram_id=telegram_id)
        self.session.add(participant)
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            # На случай гонки: уже мог добавиться параллельно
            return False
        return True

    async def list_participant_ids(self, giveaway_id: int) -> List[int]:
        res = await self.session.execute(
            select(Participant.telegram_id).where(Participant.giveaway_id == giveaway_id).order_by(Participant.joined_at.asc())
        )
        return [int(x) for x in res.scalars().all()]

    async def is_first_place_taken(self, giveaway_id: int) -> bool:
        res = await self.session.execute(select(Winner.id).where(Winner.giveaway_id == giveaway_id, Winner.position == 1))
        return res.scalar_one_or_none() is not None

    async def end_giveaway_and_store_winners(
        self,
        giveaway: Giveaway,
        *,
        winners: Sequence[Tuple[int, str | None]],
    ) -> None:
        """
        winners: последовательность (telegram_id, prize_text) в порядке позиций (1..N)
        """
        giveaway.status = "ended"
        giveaway.resolved_at = datetime.now(timezone.utc)

        # На всякий случай (если кто-то вызвал resolve повторно) чистим winners.
        await self.session.execute(delete(Winner).where(Winner.giveaway_id == giveaway.id))

        for idx, (telegram_id, prize_text) in enumerate(winners, start=1):
            self.session.add(Winner(giveaway_id=giveaway.id, telegram_id=telegram_id, position=idx, prize_text=prize_text))

        await self.session.commit()

