"""Тесты логики апгрейдера: расчёт шанса, подбор цели, розыгрыш."""
from __future__ import annotations

from collections import Counter

from bot.database.repo.known_items import KnownItem
from bot.services.upgrader_service import (
    chance_percent,
    find_nearest_target,
    roll_success,
    target_value_for_chance,
    target_value_for_multiplier,
)


def test_chance_percent_is_ratio_of_contribution_to_target():
    assert chance_percent(80, 100) == 80
    assert chance_percent(90, 100) == 90


def test_chance_percent_never_below_75():
    assert chance_percent(1, 100000) == 75
    assert chance_percent(50, 100) == 75


def test_chance_percent_clamped_to_max():
    assert chance_percent(999, 1000) <= 95


def test_target_value_for_multiplier_scales_contribution():
    assert target_value_for_multiplier(100, 2) == 200
    assert target_value_for_multiplier(100, 10) == 1000


def test_target_value_for_multiplier_always_strictly_above_contribution():
    assert target_value_for_multiplier(100, 1) > 100


def test_target_value_for_chance_is_consistent_with_chance_percent():
    contribution = 100
    for chance in (75, 80, 90):
        target = target_value_for_chance(contribution, chance)
        assert chance_percent(contribution, target) == chance


def test_find_nearest_target_picks_closest_value():
    items = [KnownItem("Cheap", 50), KnownItem("Mid", 200), KnownItem("Expensive", 1000)]
    nearest = find_nearest_target(items, target_value=210)
    assert nearest.name == "Mid"


def test_find_nearest_target_excludes_contribution_item():
    items = [KnownItem("Same", 200), KnownItem("Other", 250)]
    nearest = find_nearest_target(items, target_value=200, exclude_name="Same")
    assert nearest.name == "Other"


def test_find_nearest_target_empty_pool_returns_none():
    assert find_nearest_target([], target_value=100) is None


def test_roll_success_respects_probability_statistically():
    counts = Counter(roll_success(90) for _ in range(500))
    assert counts[True] > counts[False]

    counts_low = Counter(roll_success(10) for _ in range(500))
    assert counts_low[False] > counts_low[True]
