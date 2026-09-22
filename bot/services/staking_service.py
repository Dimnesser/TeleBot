"""Логика стейкинга: тарифы и расчёт выплаты.

[ПОДТВЕРЖДЕНО СКРИНШОТОМ] 3 тарифа (неделя +10%, 2 недели +20%, месяц
+42.9%), минимум 100 B, «забрать раньше срока нельзя».

[ЛОГИЧЕСКИ ПРЕДПОЛОЖЕНО, упрощение] Текст на скриншоте («тело вернётся
последней частью, по дням капает только надбавка») описывает подневное
капание бонуса с одной финальной выплатой тела — для этого нужен фоновый
планировщик, которого в проекте нет. Здесь заморозка выдаётся одним
платежом (тело + бонус вместе) сразу после наступления срока погашения,
без симуляции подневного капания.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from bot.database.models import StakePosition

MIN_STAKE_AMOUNT = 100


@dataclass(frozen=True)
class StakeTier:
    term_days: int
    bonus_percent: float
    label: str


STAKE_TIERS: list[StakeTier] = [
    StakeTier(term_days=7, bonus_percent=10.0, label="Неделя"),
    StakeTier(term_days=14, bonus_percent=20.0, label="2 недели"),
    StakeTier(term_days=30, bonus_percent=42.9, label="Месяц"),
]


def tier_by_term(term_days: int) -> StakeTier | None:
    return next((t for t in STAKE_TIERS if t.term_days == term_days), None)


def is_matured(position: StakePosition, now: datetime | None = None) -> bool:
    now = now or datetime.utcnow()
    return now >= position.matures_at


def bonus_amount(position: StakePosition) -> int:
    return round(position.amount * position.bonus_percent / 100)


def payout_amount(position: StakePosition) -> int:
    return position.amount + bonus_amount(position)
