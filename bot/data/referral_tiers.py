"""Тиры реферальной программы.

[ПОДТВЕРЖДЕНО СКРИНШОТОМ] Названия тиров (Бронза/Серебро/Золото/Платина/
Рубин), пороги (Старт/10+/50+/250+/750+) и комиссия Бронзы (3%).
[ЛОГИЧЕСКИ ПРЕДПОЛОЖЕНО] Комиссия для Серебра/Золота/Платины/Рубина нигде
не показана — задана возрастающей плейсхолдер-прогрессией, которую легко
заменить на реальные числа.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReferralTier:
    name: str
    min_referrals: int
    commission_percent: float


REFERRAL_TIERS: list[ReferralTier] = [
    ReferralTier("Бронза", 0, 3.0),
    ReferralTier("Серебро", 10, 4.0),
    ReferralTier("Золото", 50, 5.0),
    ReferralTier("Платина", 250, 6.0),
    ReferralTier("Рубин", 750, 8.0),
]


def tier_for_count(count: int) -> ReferralTier:
    current = REFERRAL_TIERS[0]
    for tier in REFERRAL_TIERS:
        if count >= tier.min_referrals:
            current = tier
    return current


def next_tier_for_count(count: int) -> ReferralTier | None:
    for tier in REFERRAL_TIERS:
        if count < tier.min_referrals:
            return tier
    return None
