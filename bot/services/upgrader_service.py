"""Логика апгрейдера: расчёт шанса, подбор цели по пресету, розыгрыш.

[ЛОГИЧЕСКИ ПРЕДПОЛОЖЕНО] Формула шанса нигде на скриншоте не подписана
числом — виден только индикатор «ШАНС» на круговом диске и кнопки-пресеты
«x2 / x5 / x10 / 30% / 50% / 75%». Стандартная для таких апгрейдеров формула
(и единственная, которая делает кнопки-множители и кнопки-проценты
взаимно согласованными) — chance = вклад / цель, обрезанный до разумных
границ, чтобы не было гарантированных 0%/100% исходов.
"""
from __future__ import annotations

import random

from bot.config import config
from bot.database.repo.known_items import KnownItem


def chance_percent(contribution_value: int, target_value: int) -> int:
    if target_value <= 0:
        return config.upgrader_max_chance_percent
    raw = round(contribution_value / target_value * 100)
    return max(config.upgrader_min_chance_percent, min(config.upgrader_max_chance_percent, raw))


def target_value_for_multiplier(contribution_value: int, multiplier: int) -> int:
    return max(contribution_value * multiplier, contribution_value + 1)


def target_value_for_chance(contribution_value: int, chance: int) -> int:
    chance = max(1, min(chance, 100))
    return max(round(contribution_value * 100 / chance), contribution_value + 1)


def find_nearest_target(
    known_items: list[KnownItem], target_value: int, exclude_name: str | None = None
) -> KnownItem | None:
    """Ищет известный предмет, ближайший к target_value, дороже вклада."""
    candidates = [item for item in known_items if item.name != exclude_name]
    if not candidates:
        return None
    return min(candidates, key=lambda item: abs(item.value - target_value))


def roll_success(chance: int) -> bool:
    return random.uniform(0, 100) < chance
