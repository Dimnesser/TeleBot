"""Единый каталог «известных» предметов с подтверждённой ценностью.

Используется апгрейдером как список возможных «желаемых предметов» — вместо
того, чтобы выдумывать отдельный каталог целей, переиспользуются уже
подтверждённые скриншотами названия и цены: товары обменника (DepositItem)
и дропы кейсов (CaseItem).
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.data.coins import coin_amount
from bot.database.models import CaseItem, DepositItem


@dataclass(frozen=True)
class KnownItem:
    name: str
    value: int


async def list_known_items(session: AsyncSession) -> list[KnownItem]:
    deposit_result = await session.execute(select(DepositItem.name, DepositItem.price_b))
    case_result = await session.execute(select(CaseItem.name, CaseItem.value))

    by_name: dict[str, int] = {}
    for name, value in [*deposit_result.all(), *case_result.all()]:
        if coin_amount(name) is not None:
            continue  # монеты из кейсов — не предмет
        # при дублях (одно и то же имя в разных источниках) берём большую цену
        by_name[name] = max(value, by_name.get(name, 0))

    items = [KnownItem(name=name, value=value) for name, value in by_name.items()]
    items.sort(key=lambda item: item.value)
    return items
