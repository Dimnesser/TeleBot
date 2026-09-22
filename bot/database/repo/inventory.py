"""Операции с инвентарём (предметы из кейсов и апгрейдера)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import InventoryItem, User


async def add_items(
    session: AsyncSession,
    user: User,
    source_name: str,
    item_names_and_values: list[tuple[str, int]],
    case_id: int | None = None,
) -> list[InventoryItem]:
    entries = [
        InventoryItem(user_id=user.id, case_id=case_id, case_name=source_name, item_name=name, value=value)
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


async def list_all(session: AsyncSession, user: User) -> list[InventoryItem]:
    result = await session.execute(
        select(InventoryItem).where(InventoryItem.user_id == user.id).order_by(InventoryItem.value.desc())
    )
    return list(result.scalars().all())


async def get_by_id(session: AsyncSession, item_id: int) -> InventoryItem | None:
    return await session.get(InventoryItem, item_id)


async def delete(session: AsyncSession, item: InventoryItem) -> None:
    await session.delete(item)
    await session.commit()
