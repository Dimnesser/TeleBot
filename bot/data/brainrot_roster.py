"""Реальный ростер персонажей из Roblox-игры Steal a Brainrot.

[ПОДТВЕРЖДЕНО ВЕБ-ПОИСКОМ, сентябрь 2026] Имена, тир редкости и реальная
внутриигровая экономика (цена покупки / доход в секунду в игре, в USD)
взяты с Steal a Brainrot Wiki (Fandom) и агрегаторов трейд-значений
(ItemGap, Pro Game Guides, GameRant, Digital Citizen, Beebom) через
веб-поиск. У игры НЕТ официального прайс-листа от разработчика — сами
трекеры расходятся на 20–40% день ото дня, поэтому `real_value_usd_label`
ниже — это ориентир («от Х», диапазон тира), а не биржевая котировка.

Steal a Brainrot — идле-игра «сохрани принтер денег», а не система
кейсов. Кейсы/рулетка/шансы выпадения в Brainrot Battle — это ЖАНРОВАЯ
надстройка в духе CS2 case opening поверх реального контента игры,
которую попросил сделать пользователь. Реальные имена/тиры/относительная
ценность персонажей сохранены; abсолютные числа переведены в шкалу
демо-валюты 🎫 этого бота (см. `demo_value`) степенной прогрессией по
тирам — конвертация явно вынесена в один словарь (`RARITY_VALUE_RANGE`),
чтобы её было легко поправить, если реальные цены изменятся.

Изображений персонажей здесь нет: сеть в этом окружении разрешает только
github.com/raw.githubusercontent.com, Fandom/Wikia/любые CDN с картинками
блокируются политикой egress-прокси на уровне TCP CONNECT — скачать
реальные рендеры физически невозможно из этой песочницы. Вместо фото —
процедурная «призма» тира (см. webapp/static/js/app.js, rarityTileHTML) с
инициалами персонажа. Как только появятся настоящие файлы
webapp/static/assets/brainrots/<slug>.png, фронтенд подхватит их
автоматически (img.onerror переключает на призму) — код менять не нужно.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class Rarity(str, Enum):
    COMMON = "common"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"
    MYTHIC = "mythic"
    SECRET = "secret"
    OG = "og"


RARITY_ORDER: list[Rarity] = [
    Rarity.COMMON,
    Rarity.RARE,
    Rarity.EPIC,
    Rarity.LEGENDARY,
    Rarity.MYTHIC,
    Rarity.SECRET,
    Rarity.OG,
]

RARITY_LABEL_RU: dict[Rarity, str] = {
    Rarity.COMMON: "Обычный",
    Rarity.RARE: "Редкий",
    Rarity.EPIC: "Эпический",
    Rarity.LEGENDARY: "Легендарный",
    Rarity.MYTHIC: "Мифический",
    Rarity.SECRET: "Секретный",
    Rarity.OG: "OG",
}

# Основной + акцентный цвет тира — единственное место, где заданы цвета
# редкости, дублируется 1-в-1 в webapp/static/css/app.css (см. :root).
RARITY_COLOR: dict[Rarity, tuple[str, str]] = {
    Rarity.COMMON: ("#8a93a8", "#5c6478"),
    Rarity.RARE: ("#4c9fe0", "#2e6fa8"),
    Rarity.EPIC: ("#a259e6", "#6a2fa8"),
    Rarity.LEGENDARY: ("#f0a93c", "#c9761a"),
    Rarity.MYTHIC: ("#f0435c", "#a8163a"),
    Rarity.SECRET: ("#1a1c22", "#f0c043"),
    Rarity.OG: ("#f0c043", "#ff5ec4"),
}

# Шанс выпадения по тиру (сумма = 100) — [ЛОГИЧЕСКИ ПРЕДПОЛОЖЕНО]: у Steal a
# Brainrot нет кейсов и, соответственно, нет официальных шансов дропа;
# прогрессия ниже — стандартная для case-opening жанра (CS2 и подобные),
# явно вынесена отдельным словарём для лёгкой правки.
RARITY_DROP_WEIGHT: dict[Rarity, float] = {
    Rarity.COMMON: 45.0,
    Rarity.RARE: 27.0,
    Rarity.EPIC: 15.0,
    Rarity.LEGENDARY: 8.0,
    Rarity.MYTHIC: 3.5,
    Rarity.SECRET: 1.2,
    Rarity.OG: 0.3,
}

# Диапазон демо-токенов 🎫 на тир (min, max) — сюда конвертируется реальная
# внутриигровая ценность персонажа. Один словарь = одна точка правки при
# ребалансе экономики бота, интерфейс трогать не нужно.
RARITY_VALUE_RANGE: dict[Rarity, tuple[int, int]] = {
    Rarity.COMMON: (5, 50),
    Rarity.RARE: (50, 150),
    Rarity.EPIC: (150, 500),
    Rarity.LEGENDARY: (500, 2000),
    Rarity.MYTHIC: (2000, 8000),
    Rarity.SECRET: (8000, 20000),
    Rarity.OG: (20000, 50000),
}


def slugify(name: str) -> str:
    """Имя персонажа -> путь картинки: webapp/static/assets/brainrots/<slug>.png."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


@dataclass(frozen=True)
class RosterBrainrot:
    name: str
    rarity: Rarity
    real_value_usd_label: str  # ориентир реальной внутриигровой ценности, см. докстринг модуля
    rank_in_tier: float  # 0..1, позиция внутри тира (для интерполяции в RARITY_VALUE_RANGE)

    @property
    def slug(self) -> str:
        return slugify(self.name)

    @property
    def demo_value(self) -> int:
        lo, hi = RARITY_VALUE_RANGE[self.rarity]
        return round(lo + (hi - lo) * self.rank_in_tier)


# [ПОДТВЕРЖДЕНО ВЕБ-ПОИСКОМ] rank_in_tier расставлен по реальному доходу
# ($/сек в игре) внутри тира, где он был найден в источниках; там, где
# известно только название без точного числа — по позиции в списке тира.
ROSTER: list[RosterBrainrot] = [
    # --- Common: $1/s .. $14/s (реальная цена покупки $25..$1.7K) ---
    RosterBrainrot("Noobini Pizzanini", Rarity.COMMON, "$1/сек · от $25", 0.02),
    RosterBrainrot("Lirilì Larilà", Rarity.COMMON, "$3/сек", 0.14),
    RosterBrainrot("Tim Cheese", Rarity.COMMON, "$5/сек", 0.28),
    RosterBrainrot("Fluriflura", Rarity.COMMON, "$7/сек", 0.42),
    RosterBrainrot("Talpa Di Fero", Rarity.COMMON, "$9/сек", 0.56),
    RosterBrainrot("Svinina Bombardino", Rarity.COMMON, "$10/сек", 0.66),
    RosterBrainrot("Noobini Santanini", Rarity.COMMON, "$11/сек", 0.76),
    RosterBrainrot("Tartaragno", Rarity.COMMON, "$13/сек", 0.90),
    RosterBrainrot("Pipi Kiwi", Rarity.COMMON, "$13/сек", 0.94),
    RosterBrainrot("Holy Arepa", Rarity.COMMON, "$14/сек · до $1.7K", 1.0),
    # --- Rare: $15/s .. $75/s (реальная цена $2K..$9.7K) ---
    RosterBrainrot("Trippi Troppi", Rarity.RARE, "$15/сек · от $2K", 0.0),
    RosterBrainrot("Gangster Footera", Rarity.RARE, "$30/сек", 0.25),
    RosterBrainrot("Banditto Bobritto", Rarity.RARE, "$35/сек", 0.33),
    RosterBrainrot("Boneca Ambalabu", Rarity.RARE, "$40/сек", 0.42),
    RosterBrainrot("Cacto Hipopotamo", Rarity.RARE, "$50/сек", 0.58),
    RosterBrainrot("Ta Ta Ta Ta Sahur", Rarity.RARE, "$55/сек", 0.67),
    RosterBrainrot("Cupcake Koala", Rarity.RARE, "$60/сек", 0.75),
    RosterBrainrot("Tric Trac Baraboom", Rarity.RARE, "$65/сек", 0.83),
    RosterBrainrot("Frogo Elfo", Rarity.RARE, "$67/сек", 0.87),
    RosterBrainrot("Pipi Avocado", Rarity.RARE, "$70/сек", 0.92),
    RosterBrainrot("Pengolino Nuvoletto", Rarity.RARE, "$72/сек", 0.95),
    RosterBrainrot("Pinealotto Fruttarino", Rarity.RARE, "$75/сек · до $9.7K", 1.0),
    # --- Epic: $75/s .. $325/s (реальная цена $10K..$47.5K), 2 имени подтверждены поиском ---
    RosterBrainrot("Cappuccino Assassino", Rarity.EPIC, "от $10K", 0.2),
    RosterBrainrot("Brr Brr Patapim", Rarity.EPIC, "до $47.5K", 0.8),
    # --- Legendary: $300/s .. $1900/s (реальная цена $50K..$347.5K) ---
    RosterBrainrot("Sigma Boy", Rarity.LEGENDARY, "от $50K", 0.1),
    RosterBrainrot("Chimpanzini Bananini", Rarity.LEGENDARY, "фан-фаворит", 0.35),
    RosterBrainrot("Ballerina Cappuccina", Rarity.LEGENDARY, "фан-фаворит", 0.55),
    RosterBrainrot("Chef Crabracadaba", Rarity.LEGENDARY, "нужен для Rebirth 4", 0.75),
    RosterBrainrot("Glorbo Fruttodrillo", Rarity.LEGENDARY, "до $347.5K, нужен для Rebirth 4", 0.95),
    # --- Mythic / Brainrot God: $50K/сек+ ---
    RosterBrainrot("Bombardiro Crocodilo", Rarity.MYTHIC, "топ-тир Brainrot God", 0.5),
    RosterBrainrot("Tralalero Tralala", Rarity.MYTHIC, "$50K/сек · $10M", 0.9),
    # --- Secret: $1M+/сек ---
    RosterBrainrot("Golden Skibidi", Rarity.SECRET, "единственный подтверждённый Secret", 0.3),
    RosterBrainrot("La Vacca Saturno Saturnita", Rarity.SECRET, "базовая единица трейд-листов", 0.6),
    RosterBrainrot("La Grande Combinasion", Rarity.SECRET, "$10M/сек · $1B", 1.0),
    # --- OG: топ престиж-тир игры ---
    RosterBrainrot("Meowl", Rarity.OG, "топ-тир OG", 0.2),
    RosterBrainrot("Strawberry Elephant", Rarity.OG, "топ-тир OG", 0.55),
    RosterBrainrot("Skibidi Toilet", Rarity.OG, "самый престижный OG", 1.0),
]

ROSTER_BY_RARITY: dict[Rarity, list[RosterBrainrot]] = {
    rarity: [b for b in ROSTER if b.rarity == rarity] for rarity in RARITY_ORDER
}
ROSTER_BY_NAME: dict[str, RosterBrainrot] = {b.name: b for b in ROSTER}


def infer_rarity(value: int) -> Rarity:
    """Подбирает тир редкости по значению демо-токенов (обратная RARITY_VALUE_RANGE).

    Используется там, где явного rarity нет под рукой (инвентарь после
    апгрейдера/краша/дайсов/батла — там значение получается умножением
    исходного, а не напрямую из ROSTER), чтобы визуально показать рамку/цвет
    редкости даже для производных предметов.
    """
    for rarity in RARITY_ORDER:
        lo, hi = RARITY_VALUE_RANGE[rarity]
        if lo <= value <= hi:
            return rarity
    return Rarity.OG if value > RARITY_VALUE_RANGE[Rarity.OG][1] else Rarity.COMMON
