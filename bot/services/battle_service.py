"""Логика «Батла»: 1×1 против бота-соперника на общих кейсах.

[НЕИЗВЕСТНО] Интерфейс раздела «БАТЛ» ни разу не был на скриншотах —
сделано по собственному усмотрению. Настоящий live-мультиплеер в
Telegram-боте не воспроизвести, поэтому сделан 1×1 против симулированного
бота-соперника: оба «открывают» один и тот же кейс (1, 3 или 5 раз), у кого
дороже сумма дропа — забирает все предметы, ничья — возврат входа. Работает только с
подтверждёнными открываемыми кейсами (вход — баланс B, дроп — в инвентарь, как у
остальных игровых разделов).
"""
from __future__ import annotations

from dataclasses import dataclass

from bot.database.models import CaseItem
from bot.services.cases_service import draw_items


BATTLE_QTYS = (1, 3, 5)


@dataclass(frozen=True)
class BattleResult:
    player_items: list[CaseItem]
    bot_items: list[CaseItem]
    winner: str  # "player" | "bot" | "tie"

    @property
    def player_item(self) -> CaseItem:
        return self.player_items[0]

    @property
    def bot_item(self) -> CaseItem:
        return self.bot_items[0]

    @property
    def player_total(self) -> int:
        return sum(i.value for i in self.player_items)

    @property
    def bot_total(self) -> int:
        return sum(i.value for i in self.bot_items)


def run_battle(
    items: list[CaseItem], *, qty: int = 1, luck: float | None = None, case_price: int | None = None
) -> BattleResult:
    """qty кейсов на сторону (1/3/5): побеждает бóльшая сумма дропа."""
    player_items = draw_items(items, qty, luck=luck, case_price=case_price)  # подкрутка — только игроку
    bot_items = draw_items(items, qty)
    player_total, bot_total = sum(i.value for i in player_items), sum(i.value for i in bot_items)
    if player_total > bot_total:
        winner = "player"
    elif player_total < bot_total:
        winner = "bot"
    else:
        winner = "tie"
    return BattleResult(player_items=player_items, bot_items=bot_items, winner=winner)
