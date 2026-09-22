"""Операции с розыгрышами."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import Giveaway, GiveawayEntry, GiveawayStatus, User


async def list_active(session: AsyncSession) -> list[Giveaway]:
    result = await session.execute(
        select(Giveaway).where(Giveaway.status == GiveawayStatus.ACTIVE).order_by(Giveaway.ends_at)
    )
    return list(result.scalars().all())


async def get(session: AsyncSession, giveaway_id: int) -> Giveaway | None:
    return await session.get(Giveaway, giveaway_id)


async def create(session: AsyncSession, title: str, prize_description: str, ends_at, created_by_tg_id: int) -> Giveaway:
    giveaway = Giveaway(
        title=title, prize_description=prize_description, ends_at=ends_at, created_by_tg_id=created_by_tg_id
    )
    session.add(giveaway)
    await session.commit()
    await session.refresh(giveaway)
    return giveaway


async def get_entry(session: AsyncSession, giveaway: Giveaway, user: User) -> GiveawayEntry | None:
    result = await session.execute(
        select(GiveawayEntry).where(GiveawayEntry.giveaway_id == giveaway.id, GiveawayEntry.user_id == user.id)
    )
    return result.scalar_one_or_none()


async def join(session: AsyncSession, giveaway: Giveaway, user: User) -> GiveawayEntry:
    entry = GiveawayEntry(giveaway_id=giveaway.id, user_id=user.id)
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return entry


async def count_entries(session: AsyncSession, giveaway: Giveaway) -> int:
    result = await session.execute(select(GiveawayEntry).where(GiveawayEntry.giveaway_id == giveaway.id))
    return len(result.scalars().all())


async def list_entrant_user_ids(session: AsyncSession, giveaway: Giveaway) -> list[int]:
    result = await session.execute(
        select(GiveawayEntry.user_id).where(GiveawayEntry.giveaway_id == giveaway.id)
    )
    return [row[0] for row in result.all()]


async def resolve(session: AsyncSession, giveaway: Giveaway, winner_user_id: int | None) -> Giveaway:
    giveaway.status = GiveawayStatus.RESOLVED
    giveaway.winner_user_id = winner_user_id
    await session.commit()
    await session.refresh(giveaway)
    return giveaway
