"""Логика «Батла»: 1×1 против бота-соперника на общих кейсах.

[НЕИЗВЕСТНО] Интерфейс раздела «БАТЛ» ни разу не был на скриншотах —
сделано по собственному усмотрению. Настоящий live-мультиплеер в
Telegram-боте не воспроизвести, поэтому сделан 1×1 против симулированного
бота-соперника: оба «открывают» один и тот же кейс, у кого дороже дроп —
забирает оба предмета, ничья — возврат входа. Работает только с
подтверждёнными открываемыми кейсами (вход — баланс B, дроп — в инвентарь, как у
остальных игровых разделов).
"""
from __future__ import annotations

from dataclasses import dataclass

from bot.database.models import CaseItem
from bot.services.cases_service import draw_items


@dataclass(frozen=True)
class BattleResult:
    player_item: CaseItem
    bot_item: CaseItem
    winner: str  # "player" | "bot" | "tie"


def run_battle(items: list[CaseItem]) -> BattleResult:
    player_item = draw_items(items, 1)[0]
    bot_item = draw_items(items, 1)[0]

    if player_item.value > bot_item.value:
        winner = "player"
    elif player_item.value < bot_item.value:
        winner = "bot"
    else:
        winner = "tie"

    return BattleResult(player_item=player_item, bot_item=bot_item, winner=winner)
