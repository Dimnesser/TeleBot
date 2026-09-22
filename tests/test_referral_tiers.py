"""Тесты тиров реферальной программы."""
from __future__ import annotations

from bot.data.referral_tiers import next_tier_for_count, tier_for_count


def test_tier_for_count_bronze_at_zero():
    tier = tier_for_count(0)
    assert tier.name == "Бронза"
    assert tier.commission_percent == 3.0


def test_tier_for_count_upgrades_at_threshold():
    assert tier_for_count(9).name == "Бронза"
    assert tier_for_count(10).name == "Серебро"
    assert tier_for_count(750).name == "Рубин"
    assert tier_for_count(10_000).name == "Рубин"


def test_next_tier_for_count_progression():
    assert next_tier_for_count(0).name == "Серебро"
    assert next_tier_for_count(9).name == "Серебро"
    assert next_tier_for_count(10).name == "Золото"
    assert next_tier_for_count(750) is None
