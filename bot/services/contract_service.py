"""Контракт: игрок отдаёт 3–10 своих брейнротов и получает один случайный
брейнрот ростера. Цена результата = сумма вклада × случайный множитель из
таблицы ниже (ближайший по цене брейнрот). Шансы открыты игроку.

Отдача по умолчанию 92% (настраивается в админке); в плюс выходит примерно
каждый третий контракт. Ивент «Контракт-буст» поднимает все множители.
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


def _base_ev() -> float:
    return sum(m * w for m, w in TIERS) / sum(w for _, w in TIERS)


# Отдача контракта, %: все множители масштабируются так, чтобы в среднем
# возвращалось RTP_PERCENT от вклада. Меняется в админке (app_meta
# settings_service.CONTRACT_RTP), подгружается при старте.
DEFAULT_RTP_PERCENT = 92.0
RTP_PERCENT = DEFAULT_RTP_PERCENT


def set_rtp(percent: float) -> None:
    global RTP_PERCENT
    RTP_PERCENT = float(percent)


async def load_rtp(session) -> float:
    from bot.services import settings_service
    raw = await settings_service.get_setting(session, settings_service.CONTRACT_RTP)
    try:
        set_rtp(float(raw) if raw else DEFAULT_RTP_PERCENT)
    except ValueError:
        set_rtp(DEFAULT_RTP_PERCENT)
    return RTP_PERCENT


def tiers(bonus_percent: float = 0.0) -> list[tuple[float, int]]:
    """Таблица с учётом отдачи и ивента «Контракт-буст» (+X% к множителю)."""
    k = RTP_PERCENT / 100 / _base_ev() * (1 + bonus_percent / 100)
    return [(round(m * k, 2), w) for m, w in TIERS]


def expected_multiplier(bonus_percent: float = 0.0) -> float:
    t = tiers(bonus_percent)
    return sum(m * w for m, w in t) / sum(w for _, w in t)


def roll_multiplier(rng: random.Random | None = None, bonus_percent: float = 0.0) -> float:
    rng = rng or random
    t = tiers(bonus_percent)
    mult = rng.choices([m for m, _ in t], weights=[w for _, w in t])[0]
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
    t = tiers()
    lo, hi = stake * t[0][0] * 0.9, stake * t[-1][0] * 1.1
    inside = [(nm, v) for nm, v in pool if lo <= v <= hi] or pool
    return [rng.choice(inside) for _ in range(n - 1)] + [won]
