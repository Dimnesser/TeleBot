"""Операции с инвентарём (предметы из кейсов и апгрейдера)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.data.brainrot_roster import rarity_for
from bot.database.models import InventoryItem, User


async def add_items(
    session: AsyncSession,
    user: User,
    source_name: str,
    item_names_and_values: list[tuple[str, int]],
    case_id: int | None = None,
    *,
    commit: bool = True,
) -> list[InventoryItem]:
    # rarity — реальный тир персонажа из ростера (rarity_for); по ценности
    # угадывается только для имён вне ростера. Вызывающему коду
    # (кейсы/апгрейдер/краш/дайсы/батл) её прокидывать не нужно.
    entries = [
        InventoryItem(
            user_id=user.id,
            case_id=case_id,
            case_name=source_name,
            item_name=name,
            value=value,
            rarity=rarity_for(name, value).value,
        )
        for name, value in item_names_and_values
    ]
    session.add_all(entries)
    if commit:
        await session.commit()
    else:
        await session.flush()
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


async def list_recent_global(session: AsyncSession, limit: int = 20) -> list[tuple[InventoryItem, User]]:
    """Последние выигрыши по всем пользователям — для ленты «последние выигрыши» на главной."""
    result = await session.execute(
        select(InventoryItem, User)
        .join(User, User.id == InventoryItem.user_id)
        .order_by(InventoryItem.obtained_at.desc())
        .limit(limit)
    )
    return [(row[0], row[1]) for row in result.all()]


async def get_by_id(session: AsyncSession, item_id: int) -> InventoryItem | None:
    return await session.get(InventoryItem, item_id)


async def delete(session: AsyncSession, item: InventoryItem) -> None:
    await session.delete(item)
    await session.commit()
