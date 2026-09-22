"""Операции с каталогом предметов для депозита."""
from __future__ import annotations

from sqlalchemy import asc, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import DepositCategory, DepositItem


async def list_items(
    session: AsyncSession,
    category: DepositCategory,
    search: str | None = None,
    price_min: int | None = None,
    price_max: int | None = None,
    sort_desc: bool = False,
) -> list[DepositItem]:
    query = select(DepositItem).where(
        DepositItem.category == category,
        DepositItem.is_active.is_(True),
    )
    if search:
        query = query.where(DepositItem.name.ilike(f"%{search}%"))
    if price_min is not None:
        query = query.where(DepositItem.price_b >= price_min)
    if price_max is not None:
        query = query.where(DepositItem.price_b <= price_max)

    order = desc(DepositItem.price_b) if sort_desc else asc(DepositItem.sort_order)
    query = query.order_by(order)

    result = await session.execute(query)
    return list(result.scalars().all())


async def get_item(session: AsyncSession, item_id: int) -> DepositItem | None:
    return await session.get(DepositItem, item_id)
