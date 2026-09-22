"""Операции с инвентарём (предметы, выпавшие из кейсов)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import Case, InventoryItem, User


async def add_items(
    session: AsyncSession, user: User, case: Case, item_names_and_values: list[tuple[str, int]]
) -> list[InventoryItem]:
    entries = [
        InventoryItem(user_id=user.id, case_id=case.id, case_name=case.name, item_name=name, value=value)
        for name, value in item_names_and_values
    ]
    session.add_all(entries)
    await session.commit()
    return entries


async def list_recent(session: AsyncSession, user: User, limit: int = 10) -> list[InventoryItem]:
    result = await session.execute(
        select(InventoryItem)
        .where(InventoryItem.user_id == user.id)
        .order_by(InventoryItem.obtained_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
