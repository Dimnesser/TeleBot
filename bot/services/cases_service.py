"""Логика открытия кейсов: вес дропа и подсчёт стоимости."""
from __future__ import annotations

import random

from bot.database.models import Case, CaseItem


def item_weight(item: CaseItem) -> float:
    """Вес предмета ∝ 1/ценность.

    Ценность выведена из реальной внутриигровой цены персонажа, поэтому
    дорогой в игре персонаж настолько же редок в кейсе. Побочный эффект
    такого веса — каждый предмет вносит в средний дроп одинаковый вклад,
    и цену кейса можно честно посчитать из содержимого
    (bot.data.seed_cases.price_for).
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


REEL_LENGTH = 40
REEL_REVEAL_INDEX = 34


def build_reel(items: list[CaseItem], winner: CaseItem, *, length: int = REEL_LENGTH, reveal_index: int = REEL_REVEAL_INDEX) -> list[CaseItem]:
    """Строит ленту для рулетки открытия: результат уже определён сервером
    (`winner` — из уже вызванного draw_items), лента — только визуальный
    антураж под него. Клиент не может повлиять на исход: winner ставится
    на фиксированную позицию `reveal_index`, остальные позиции — обычный
    взвешенный розыгрыш по тем же весам, что и настоящий дроп (не
    подыгрывает и не отбирает у реального результата вероятность).
    """
    if not items:
        return [winner] * length
    weights = [item_weight(item) for item in items]
    reel = random.choices(items, weights=weights, k=length)
    reel[reveal_index] = winner
    return reel
