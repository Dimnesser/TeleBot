"""Стартовый каталог предметов для приёма депозитов.

[ПОДТВЕРЖДЕНО СКРИНШОТОМ] Названия, цены в B и «от N шт.» взяты напрямую со
скриншотов разделов «Депозит брейнротом» и «Депозит гирсами». Иконки-эмодзи —
приближение: в оригинале это кастомная пиксель-арт графика, которую Telegram
не позволяет прикрепить как emoji, поэтому подобраны смысловые аналоги.
Список редактируется через БД (таблица deposit_items) — это лишь сид на первый запуск.
"""
from __future__ import annotations

from dataclasses import dataclass

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
    # Брейнроты
    SeedItem(DepositCategory.BRAINROT, "Kraken", "🐙", 3077, 1, 15, 1),
    SeedItem(DepositCategory.BRAINROT, "Garama and Madundung", "🗿", 41, 2, None, 2),
    SeedItem(DepositCategory.BRAINROT, "Cash or Card", "💳", 43, 2, None, 3),
    SeedItem(DepositCategory.BRAINROT, "Burguro And Fryuro", "🍔", 73, 1, None, 4),
    SeedItem(DepositCategory.BRAINROT, "Pizza and Ranch", "🍕", 80, 1, None, 5),
    SeedItem(DepositCategory.BRAINROT, "Popcuru and Fizzuru", "🍿", 87, 1, None, 6),
    SeedItem(DepositCategory.BRAINROT, "Capitano Moby", "🐋", 91, 1, None, 7),
    SeedItem(DepositCategory.BRAINROT, "Celestial Pegasus", "🦄", 93, 1, None, 8),
]
