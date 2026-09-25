"""Выдача дропа игроку: монеты B — на баланс, брейнроты — в инвентарь,
всё — в журнал ленты «Последние выигрыши» (DropLog)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.data.brainrot_roster import rarity_for
from bot.data.coins import COIN_RARITY, coin_amount
from bot.database.models import DropLog, InventoryItem, User
from bot.database.repo import inventory as inventory_repo


async def grant(
    session: AsyncSession, user: User, source: str, items: list[tuple[str, int]], *, case_id: int | None = None,
) -> list[InventoryItem | None]:
    """items — (имя, ценность). Возвращает записи инвентаря в том же порядке
    (None для монет). Коммитит."""
    coins = sum(coin_amount(name) or 0 for name, _ in items)
    if coins:
        user.balance += coins
    brainrots = [(n, v) for n, v in items if coin_amount(n) is None]
    entries = iter(await inventory_repo.add_items(session, user, source, brainrots, case_id=case_id, commit=False))
    session.add_all(
        DropLog(user_id=user.id, item_name=n, value=v, source=source,
                rarity=COIN_RARITY if coin_amount(n) is not None else rarity_for(n, v).value)
        for n, v in items
    )
    result = [None if coin_amount(n) is not None else next(entries) for n, _ in items]
    await session.commit()
    return result


async def log(session: AsyncSession, user: User, source: str, items: list[tuple[str, int]]) -> None:
    """Только запись в ленту (предмет уже выдан другим путём)."""
    session.add_all(DropLog(user_id=user.id, item_name=n, value=v, source=source, rarity=rarity_for(n, v).value)
                    for n, v in items)
    await session.commit()


async def recent(session: AsyncSession, limit: int = 20, *, min_value: int = 1) -> list[tuple[DropLog, User]]:
    rows = await session.execute(
        select(DropLog, User).join(User, User.id == DropLog.user_id)
        .where(DropLog.rarity != COIN_RARITY, DropLog.value >= min_value)
        .order_by(DropLog.id.desc()).limit(limit)
    )
    return [(r[0], r[1]) for r in rows.all()]
