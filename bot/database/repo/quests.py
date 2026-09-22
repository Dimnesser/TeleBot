"""Операции с квестами и прогрессом пользователя по ним."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import Quest, QuestScope, User, UserQuestProgress


async def list_quests(session: AsyncSession) -> list[Quest]:
    result = await session.execute(select(Quest).order_by(Quest.scope, Quest.sort_order))
    return list(result.scalars().all())


async def list_quests_by_target(session: AsyncSession, target_type: str) -> list[Quest]:
    result = await session.execute(select(Quest).where(Quest.target_type == target_type))
    return list(result.scalars().all())


async def get_progress(
    session: AsyncSession, user: User, quest: Quest, period_key: str
) -> UserQuestProgress | None:
    result = await session.execute(
        select(UserQuestProgress).where(
            UserQuestProgress.user_id == user.id,
            UserQuestProgress.quest_id == quest.id,
            UserQuestProgress.period_key == period_key,
        )
    )
    return result.scalar_one_or_none()


async def get_or_create_progress(
    session: AsyncSession, user: User, quest: Quest, period_key: str
) -> UserQuestProgress:
    progress = await get_progress(session, user, quest, period_key)
    if progress:
        return progress
    progress = UserQuestProgress(user_id=user.id, quest_id=quest.id, period_key=period_key, progress_count=0)
    session.add(progress)
    await session.commit()
    await session.refresh(progress)
    return progress
