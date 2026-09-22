"""Логика розыгрышей: проверка истечения срока и выбор победителя.

[НЕИЗВЕСТНО] Интерфейс раздела «Розыгрыши» ни разу не был на скриншотах —
сделано по собственному усмотрению (см. комментарий у Giveaway в моделях).
Розыгрыш завершается «лениво»: при каждом открытии раздела проверяются
активные розыгрыши, и просроченные разыгрываются на месте — отдельного
планировщика фоновых задач для этого нет.
"""
from __future__ import annotations

import random
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import Giveaway, GiveawayStatus
from bot.database.repo import giveaways as giveaways_repo


def is_expired(giveaway: Giveaway, now: datetime | None = None) -> bool:
    now = now or datetime.utcnow()
    return now >= giveaway.ends_at


async def resolve_if_expired(session: AsyncSession, giveaway: Giveaway) -> Giveaway:
    if giveaway.status != GiveawayStatus.ACTIVE or not is_expired(giveaway):
        return giveaway

    entrant_ids = await giveaways_repo.list_entrant_user_ids(session, giveaway)
    winner_id = random.choice(entrant_ids) if entrant_ids else None
    return await giveaways_repo.resolve(session, giveaway, winner_id)


async def resolve_all_expired(session: AsyncSession) -> list[Giveaway]:
    active = await giveaways_repo.list_active(session)
    resolved = []
    for giveaway in active:
        if is_expired(giveaway):
            resolved.append(await resolve_if_expired(session, giveaway))
    return resolved
