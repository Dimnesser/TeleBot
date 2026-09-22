"""Операции со стейкингом реального баланса B."""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import StakePosition, StakeStatus, User


async def get_active_position(session: AsyncSession, user: User) -> StakePosition | None:
    """Один активный стейк на аккаунт (см. заголовок раздела на скриншоте)."""
    result = await session.execute(
        select(StakePosition).where(StakePosition.user_id == user.id, StakePosition.status == StakeStatus.ACTIVE)
    )
    return result.scalar_one_or_none()


async def create_position(
    session: AsyncSession, user: User, amount: int, term_days: int, bonus_percent: float
) -> StakePosition:
    now = datetime.utcnow()
    position = StakePosition(
        user_id=user.id,
        amount=amount,
        term_days=term_days,
        bonus_percent=bonus_percent,
        started_at=now,
        matures_at=now + timedelta(days=term_days),
    )
    session.add(position)
    await session.commit()
    await session.refresh(position)
    return position


async def list_completed(session: AsyncSession, user: User) -> list[StakePosition]:
    result = await session.execute(
        select(StakePosition).where(StakePosition.user_id == user.id, StakePosition.status == StakeStatus.COMPLETED)
    )
    return list(result.scalars().all())


async def list_all_for_user(session: AsyncSession, user: User) -> list[StakePosition]:
    result = await session.execute(select(StakePosition).where(StakePosition.user_id == user.id))
    return list(result.scalars().all())


async def get_position(session: AsyncSession, position_id: int) -> StakePosition | None:
    return await session.get(StakePosition, position_id)


async def save(session: AsyncSession, position: StakePosition) -> StakePosition:
    await session.commit()
    await session.refresh(position)
    return position
