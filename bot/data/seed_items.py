"""Стартовый каталог предметов для приёма депозитов.

[ПОДТВЕРЖДЕНО СКРИНШОТОМ] Названия, цены в B и «от N шт.» взяты напрямую со
скриншотов разделов «Депозит брейнротом» и «Депозит гирсами». Иконки-эмодзи —
приближение: в оригинале это кастомная пиксель-арт графика, которую Telegram
не позволяет прикрепить как emoji, поэтому подобраны смысловые аналоги.
Список редактируется через БД (таблица deposit_items) — это лишь сид на первый запуск.
"""
from __future__ import annotations

from dataclasses import dataclass

from bot.data.brainrot_roster import CHEAP_SECRETS, ROSTER
from bot.database.models import DepositCategory


@dataclass(frozen=True)
class SeedItem:
    category: DepositCategory
    name: str
    emoji: str
    price_b: int
    min_qty: int
    hot_stock_left: int | None
    sort_order: int


SEED_ITEMS: list[SeedItem] = [
    # Гирсы
    SeedItem(DepositCategory.HIRSY, "Cupid Wings", "🪽", 34, 2, None, 1),
    SeedItem(DepositCategory.HIRSY, "Wave Rider", "🏄", 35, 2, None, 2),
    SeedItem(DepositCategory.HIRSY, "Witch Broom", "🧹", 38, 2, None, 3),
    SeedItem(DepositCategory.HIRSY, "Santas Sleigh", "🛷", 88, 1, None, 4),
    SeedItem(DepositCategory.HIRSY, "Rainbow Hammer", "🔨", 623, 1, None, 5),
    SeedItem(DepositCategory.HIRSY, "Bloodmoon Hammer", "🔨", 1259, 1, None, 6),
    # Брейнроты — из ростера (bot.data.brainrot_roster), см. BRAINROT_DEPOSIT_ITEMS ниже.
]


# Приём брейнротов — те же 57 брейнротов и цены в B, что на скриншотах
# «Депозит брейнротом» (= основной ростер). Дешёвые Secret из кейсов обменник
# не принимает — на скриншоте самый дешёвый приём Garama and Madundung (41 B).
# «от 2 шт» — у дешёвых (< 50 B), как у Cash or Card и Garama на скриншоте.
_CHEAP = {b.name for b in CHEAP_SECRETS}
_HOT_STOCK = {"Kraken": 15}
BRAINROT_DEPOSIT_ITEMS: list[SeedItem] = [
    SeedItem(DepositCategory.BRAINROT, b.name, "🧠", b.value, 2 if b.value < 50 else 1, _HOT_STOCK.get(b.name), n)
    for n, b in enumerate(sorted((b for b in ROSTER if b.name not in _CHEAP), key=lambda b: b.value), start=1)
]
SEED_ITEMS = SEED_ITEMS + BRAINROT_DEPOSIT_ITEMS
DEPOSIT_CATALOG_VERSION = "2-roster"
