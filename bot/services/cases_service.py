"""Логика открытия кейсов: вес дропа и подсчёт стоимости."""
from __future__ import annotations

import random

from bot.database.models import Case, CaseItem


# Вес предмета ∝ 1/ценность^k. При k > 1 дорогие брейнроты выпадают заметно
# реже, чем «пропорционально цене» — кейс тяжело окупить. Та же степень
# используется при расчёте цены кейса (bot.data.seed_cases.price_for).
CASE_WEIGHT_EXPONENT = 1.5


def item_weight(item: CaseItem) -> float:
    return 1.0 / max(item.value, 1) ** CASE_WEIGHT_EXPONENT


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
