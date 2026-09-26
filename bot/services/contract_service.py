"""Контракт: игрок отдаёт 3–10 своих брейнротов и получает один случайный
брейнрот ростера. Цена результата = сумма вклада × случайный множитель из
таблицы ниже (ближайший по цене брейнрот). Шансы открыты игроку.

Средний множитель ≈ 0.93 — чуть в минус, как и остальные режимы; в плюс
(×1.1 и выше) выходит примерно каждый третий контракт.
"""
from __future__ import annotations

import random

MIN_ITEMS = 3
MAX_ITEMS = 10

# (множитель, шанс %) — сумма шансов 100.
TIERS: list[tuple[float, int]] = [
    (0.4, 35),
    (0.7, 27),
    (1.1, 20),
    (1.6, 11),
    (2.5, 5),
    (4.0, 2),
]
MIN_MULT = TIERS[0][0]
MAX_MULT = TIERS[-1][0]


def expected_multiplier() -> float:
    return sum(m * w for m, w in TIERS) / sum(w for _, w in TIERS)


def roll_multiplier(rng: random.Random | None = None) -> float:
    rng = rng or random
    mult = rng.choices([m for m, _ in TIERS], weights=[w for _, w in TIERS])[0]
    return mult * rng.uniform(0.9, 1.1)  # немного разброса внутри тира


def pick_result(pool: list[tuple[str, int]], stake: int, mult: float,
                rng: random.Random | None = None) -> tuple[str, int]:
    """Брейнрот из pool (имя, цена), ближайший к stake × mult. Среди почти
    равных по близости — случайный, чтобы не выпадал всегда один и тот же."""
    rng = rng or random
    want = stake * mult
    best = min(abs(v - want) for _, v in pool)
    near = [(n, v) for n, v in pool if abs(v - want) <= best * 1.15 + 1]
    return rng.choice(near)


def reel(pool: list[tuple[str, int]], stake: int, won: tuple[str, int], n: int = 18,
         rng: random.Random | None = None) -> list[tuple[str, int]]:
    """Брейнроты для анимации перебора: из диапазона контракта, в конце — выигрыш."""
    rng = rng or random
    lo, hi = stake * MIN_MULT * 0.9, stake * MAX_MULT * 1.1
    inside = [(nm, v) for nm, v in pool if lo <= v <= hi] or pool
    return [rng.choice(inside) for _ in range(n - 1)] + [won]
