"""Монеты как дроп кейса: предмет «🪙 N» при выигрыше сразу зачисляется
на баланс B, а не кладётся в инвентарь."""
from __future__ import annotations

COIN_PREFIX = "🪙 "
# Старые записи каталога/ленты могли сохраниться с прежним префиксом.
LEGACY_COIN_PREFIXES = ("🎫 ",)
COIN_RARITY = "coins"


def coin_name(amount: int) -> str:
    return f"{COIN_PREFIX}{amount}"


def coin_amount(name: str) -> int | None:
    prefix = next((p for p in (COIN_PREFIX, *LEGACY_COIN_PREFIXES) if name.startswith(p)), None)
    if prefix is None:
        return None
    tail = name[len(prefix):]
    return int(tail) if tail.isdigit() else None
