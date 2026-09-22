"""Тесты логики дайсов: бросок и таблица выплат."""
from __future__ import annotations

from unittest.mock import patch

from bot.services.dice_service import COLORS, DICE_COUNT, MATCH_PAYOUT_TABLE, resolve_roll, roll_dice


def test_roll_dice_returns_correct_count_from_palette():
    dice = roll_dice()
    assert len(dice) == DICE_COUNT
    assert all(d in COLORS for d in dice)


def test_payout_table_matches_screenshot_exactly():
    assert MATCH_PAYOUT_TABLE == {0: None, 1: 2.0, 2: None, 3: None, 4: 3.0}


def test_resolve_roll_match_count_is_consistent_without_bonus():
    with patch("bot.services.dice_service.random.uniform", return_value=100.0):  # никогда не бонус
        for _ in range(100):
            result = resolve_roll(chosen_color="🔴")
            actual_matches = sum(1 for d in result.dice if d == "🔴")
            assert result.match_count == actual_matches
            assert result.bonus is False
            assert result.multiplier == MATCH_PAYOUT_TABLE[result.match_count]


def test_resolve_roll_bonus_overrides_table_with_bonus_multiplier():
    with patch("bot.services.dice_service.random.uniform", return_value=0.0):  # всегда бонус
        result = resolve_roll(chosen_color="🔵")
        assert result.bonus is True
        assert result.multiplier == 10.0
        assert result.is_win is True


def test_dice_result_is_win_false_on_losing_match_count():
    with patch("bot.services.dice_service.random.uniform", return_value=100.0):
        with patch("bot.services.dice_service.random.choice", return_value="🟢"):
            result = resolve_roll(chosen_color="🔴")  # 0 совпадений -> проигрыш
            assert result.match_count == 0
            assert result.is_win is False
