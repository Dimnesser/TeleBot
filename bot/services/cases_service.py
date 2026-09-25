"""Логика открытия кейсов: вес дропа и подсчёт стоимости."""
from __future__ import annotations

import random

from bot.database.models import Case, CaseItem


# Вес предмета ∝ 1/ценность^k. k = 0.8 — дорогие брейнроты реже дешёвых, но
# топ кейса выпадает в 1–4% открытий (при k = 1 было 0.1–3%). Та же степень —
# в расчёте цены (seed_cases.price_for).
CASE_WEIGHT_EXPONENT = 0.8


def item_weight(item: CaseItem) -> float:
    """Доля из балансировки кейса (seed_cases.balanced_weights), иначе 1/ценность^k."""
    weight = getattr(item, "weight", None)
    if weight is not None:
        return weight
    return 1.0 / max(item.value, 1) ** CASE_WEIGHT_EXPONENT


def total_cost(case: Case, quantity: int) -> int | None:
    """Цена открытия quantity кейсов — с учётом ивента скидки."""
    from bot.services import events_service

    if case.price_tokens is None:
        return None
    return events_service.price(case.price_tokens) * quantity


def draw_items(
    items: list[CaseItem], quantity: int, *, luck: float | None = None, case_price: int | None = None
) -> list[CaseItem]:
    """luck — подкрутка админа для игрока (User.luck): вес предметов, которые
    окупают кейс (ценность ≥ цены; у бесплатного — дороже медианы), × luck.
    >1 — чаще окупается, <1 — реже, 0 — не окупается никогда; None — честные веса."""
    if not items:
        return []
    weights = [item_weight(item) for item in items]
    if luck is not None and luck != 1:
        threshold = case_price or sorted(i.value for i in items)[len(items) // 2]
        weights = [w * luck if i.value >= threshold else w for w, i in zip(weights, items)]
        if not any(weights):  # всё в кейсе окупает его — при ×0 падает самое дешёвое
            return [min(items, key=lambda i: i.value)] * quantity
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
