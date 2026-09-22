"""Логика дайсов: бросок 4 кубиков и таблица выплат.

[ПОДТВЕРЖДЕНО СКРИНШОТОМ] Таблица «Правила игры» дана как есть: строки
пронумерованы 1–5 с подписями «0/4…4/4» — это количество кубиков,
совпавших с выбранным цветом — и явным исходом:
  0/4 → проигрыш, 1/4 → x2, 2/4 → проигрыш, 3/4 → проигрыш, 4/4 → x3.
Строка «БОНУС» с радужной иконкой стоит отдельно, без своей «N/4», поэтому
это независимое редкое событие (а не замена строки «4/4») —
[ЛОГИЧЕСКИ ПРЕДПОЛОЖЕНО] здесь реализовано как отдельный шанс (config
DICE_BONUS_CHANCE_PERCENT), проверяемый до таблицы совпадений и
перекрывающий её результат, если сработал.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from bot.config import config

COLORS: list[str] = ["🔴", "🟠", "🟡", "🟢", "🔵", "🟣"]
DICE_COUNT = 4

# [ПОДТВЕРЖДЕНО СКРИНШОТОМ] точная таблица совпадений → множитель (None = проигрыш).
MATCH_PAYOUT_TABLE: dict[int, float | None] = {0: None, 1: 2.0, 2: None, 3: None, 4: 3.0}


@dataclass(frozen=True)
class DiceResult:
    dice: list[str]
    match_count: int
    bonus: bool
    multiplier: float | None

    @property
    def is_win(self) -> bool:
        return self.multiplier is not None


def roll_dice() -> list[str]:
    return [random.choice(COLORS) for _ in range(DICE_COUNT)]


def resolve_roll(chosen_color: str) -> DiceResult:
    dice = roll_dice()
    match_count = sum(1 for d in dice if d == chosen_color)

    if random.uniform(0, 100) < config.dice_bonus_chance_percent:
        return DiceResult(dice=dice, match_count=match_count, bonus=True, multiplier=config.dice_bonus_multiplier)

    multiplier = MATCH_PAYOUT_TABLE.get(match_count)
    return DiceResult(dice=dice, match_count=match_count, bonus=False, multiplier=multiplier)
