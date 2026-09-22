"""Тесты логики краша: рост множителя и точка обрыва."""
from __future__ import annotations

from bot.config import config
from bot.services.crash_service import generate_crash_point, multiplier_at


def test_multiplier_at_zero_is_one():
    assert multiplier_at(0) == 1.0


def test_multiplier_grows_with_elapsed_time():
    early = multiplier_at(config.crash_tick_seconds)
    later = multiplier_at(config.crash_tick_seconds * 10)
    assert later > early > 1.0


def test_multiplier_is_capped_at_max_multiplier():
    huge_elapsed = config.crash_tick_seconds * 10_000
    assert multiplier_at(huge_elapsed) == config.crash_max_multiplier


def test_generate_crash_point_never_below_one():
    for _ in range(200):
        assert generate_crash_point() >= 1.00


def test_generate_crash_point_capped_at_max_multiplier():
    for _ in range(200):
        assert generate_crash_point() <= config.crash_max_multiplier


def test_generate_crash_point_mostly_low_with_rare_high_values():
    points = [generate_crash_point() for _ in range(500)]
    below_three = sum(1 for p in points if p < 3.0)
    # хвостатое распределение 1/U: большинство раундов должны обрываться рано
    assert below_three > len(points) * 0.5
