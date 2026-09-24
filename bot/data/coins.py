"""Монеты как дроп кейса: предмет «🎫 N» при выигрыше сразу зачисляется
на демо-баланс, а не кладётся в инвентарь."""
from __future__ import annotations

COIN_PREFIX = "🎫 "
COIN_RARITY = "coins"


def coin_name(amount: int) -> str:
    return f"{COIN_PREFIX}{amount}"


def coin_amount(name: str) -> int | None:
    if not name.startswith(COIN_PREFIX):
        return None
    tail = name[len(COIN_PREFIX):]
    return int(tail) if tail.isdigit() else None
