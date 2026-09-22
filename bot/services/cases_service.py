"""Логика открытия кейсов: вес дропа и подсчёт стоимости."""
from __future__ import annotations

import random

from bot.database.models import Case, CaseItem


def item_weight(item: CaseItem) -> float:
    """Вес предмета в случайном розыгрыше.

    [ЛОГИЧЕСКИ ПРЕДПОЛОЖЕНО] Проценты выпадения нигде на скриншотах не
    показаны (в отличие, например, от «Дайсов»). Единственная видимая
    зависимость — список «Что может выпасть» отсортирован от дорогого к
    дешёвому, что в лутбоксах почти всегда означает «дороже — реже».
    Здесь используется обратная зависимость от стоимости: вес = 1 / value.
    Легко заменить на точные проценты, если они станут известны.
    """
    return 1.0 / max(item.value, 1)


def total_cost(case: Case, quantity: int) -> int | None:
    if case.price_tokens is None:
        return None
    return case.price_tokens * quantity


def draw_items(items: list[CaseItem], quantity: int) -> list[CaseItem]:
    if not items:
        return []
    weights = [item_weight(item) for item in items]
    return random.choices(items, weights=weights, k=quantity)
