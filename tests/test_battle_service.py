"""Тесты логики батла: определение победителя."""
from __future__ import annotations

from unittest.mock import patch

from bot.database.models import CaseItem
from bot.services.battle_service import run_battle


def make_item(item_id: int, value: int) -> CaseItem:
    return CaseItem(id=item_id, case_id=1, name=f"Item {item_id}", value=value)


def test_battle_higher_value_wins():
    cheap = make_item(1, 10)
    expensive = make_item(2, 1000)
    with patch("bot.services.battle_service.draw_items", side_effect=[[cheap], [expensive]]):
        result = run_battle([cheap, expensive])
    assert result.winner == "bot"
    assert result.player_item is cheap
    assert result.bot_item is expensive


def test_battle_player_wins_when_drawn_higher():
    cheap = make_item(1, 10)
    expensive = make_item(2, 1000)
    with patch("bot.services.battle_service.draw_items", side_effect=[[expensive], [cheap]]):
        result = run_battle([cheap, expensive])
    assert result.winner == "player"


def test_battle_tie_on_equal_value():
    item_a = make_item(1, 100)
    item_b = make_item(2, 100)
    with patch("bot.services.battle_service.draw_items", side_effect=[[item_a], [item_b]]):
        result = run_battle([item_a, item_b])
    assert result.winner == "tie"
