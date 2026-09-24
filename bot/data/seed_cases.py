"""Каталог кейсов BrainCore.

Каждый кейс назван по своему «герою» — самому дорогому брейнроту внутри
(он же сидит в модели кейса), остальное — лестница дешевле. Содержимое —
только реальные персонажи Steal a Brainrot из bot.data.brainrot_roster
(ценности со скриншотов пользователя) и, в бесплатных кейсах, монеты.

Логика кейса (вся выводится из данных, руками не проставлено ничего):
  * ценность предмета 🎫 — его ценность в B со скриншотов пользователя
    (brainrot_roster.ROSTER);
  * шанс предмета ∝ 1 / ценность^1.5 — дорогие брейнроты заметно реже,
    чем пропорционально цене (bot.services.cases_service.item_weight);
  * цена кейса = средний дроп / TARGET_RTP, округлённая вверх — кейс
    возвращает в среднем 60% своей цены, окупить его тяжело.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from bot.data.brainrot_roster import ROSTER_BY_NAME
from bot.data.coins import COIN_RARITY, coin_name
from bot.database.models import CaseCategory
from bot.services.cases_service import CASE_WEIGHT_EXPONENT

CASES_CONTENT_VERSION = "14.1-hero-cases"

TARGET_RTP = 0.6


@dataclass(frozen=True)
class SeedCaseItem:
    name: str
    value: int
    rarity: str | None = None


@dataclass(frozen=True)
class CaseTheme:
    """Модель кейса — рисуется фронтендом (webapp/static/js/case-themes.js):
    открытый кейс-чемодан с цветом корпуса shell, наполнителем filling, в
    котором сидят герои кейса, и аурой aura вокруг."""

    filling: str  # coins | junk | sand | wood | food | noodles | pumpkins | bills | water | bolts | gifts | candy | crystals | embers | smoke | snow | strawberries
    aura: str  # none | sparkle | dust | stars | smoke | lightning | fire | bubbles | confetti | crystal | snow | leaves
    shell: tuple[str, str]  # светлый и тёмный тон корпуса
    accent: str  # цвет свечения/акцентов


@dataclass(frozen=True)
class SeedCase:
    category: CaseCategory
    code: str
    name: str
    price_tokens: int | None
    item_count_label: int | None
    note: str | None = None
    items: tuple[SeedCaseItem, ...] = field(default_factory=tuple)
    sort_order: int = 0

    @property
    def is_openable(self) -> bool:
        return len(self.items) > 0


def expected_value(values: list[int]) -> float:
    """Средний дроп при весах 1/value^k (см. cases_service.CASE_WEIGHT_EXPONENT)."""
    weights = [v ** -CASE_WEIGHT_EXPONENT for v in values]
    return sum(v * w for v, w in zip(values, weights)) / sum(weights)


def price_for(values: list[int]) -> int:
    return math.ceil(expected_value(values) / TARGET_RTP)


def _pool(names: list[str | int]) -> tuple[SeedCaseItem, ...]:
    """Имена брейнротов из ростера; число N — монеты «🎫 N» (сразу на баланс)."""
    items = [
        SeedCaseItem(coin_name(n), n, COIN_RARITY) if isinstance(n, int)
        else SeedCaseItem(n, ROSTER_BY_NAME[n].value, ROSTER_BY_NAME[n].rarity.value)
        for n in names
    ]
    return tuple(sorted(items, key=lambda i: i.value, reverse=True))


CASE_THEMES: dict[str, CaseTheme] = {}


def _case(
    category: CaseCategory, code: str, name: str, sort_order: int, theme: CaseTheme, names: list[str | int],
    price: int | None = None,
) -> SeedCase:
    items = _pool(names)
    CASE_THEMES[code] = theme
    return SeedCase(
        category=category,
        code=code,
        name=name,
        price_tokens=price if price is not None else price_for([i.value for i in items]),
        item_count_label=len(items),
        items=items,
        sort_order=sort_order,
    )


K, A = CaseCategory.STARTER, CaseCategory.APEX

SEED_CASES: list[SeedCase] = [
    # ------------------------------------------------------------ БЕСПЛАТНЫЕ
    _case(
        CaseCategory.FREE, "free", "Бесплатный", 1,
        CaseTheme("junk", "none", ("#b08455", "#5e3d1f"), "#e0b98a"),
        [1, 2, 3, 5, 10, "Noobini Pizzanini", "Lirilì Larilà", "Tim Cheese", "Fluriflura", "Pipi Kiwi", "Talpa Di Fero"],
        price=0,
    ),
    # Не продаётся: открывается только бесплатными открытиями, которые
    # выдаёт партнёрский код (bot.services.partner_service).
    _case(
        CaseCategory.REFERRAL, "referral", "Реферальный", 2,
        CaseTheme("coins", "sparkle", ("#2c2c31", "#0c0c0f"), "#ffc93c"),
        [1, 2, 3, 5, "Noobini Pizzanini", "Tim Cheese", "Pipi Kiwi", "Trippi Troppi", "Boneca Ambalabu"],
    ),
    # ------------------------------------------------------------ КЕЙСЫ
    _case(K, "sandbox", "Песочница", 1, CaseTheme("sand", "dust", ("#e2b765", "#8a5a1c"), "#ffe2a0"),
          ["Bombardiro Crocodilo", "Cappuccino Assassino", "Brr Brr Patapim", "Boneca Ambalabu", "Gangster Footera",
           "Trippi Troppi", "Pipi Kiwi", "Svinina Bombardino", "Talpa Di Fero", "Fluriflura", "Tim Cheese",
           "Lirilì Larilà", "Noobini Pizzanini"]),
    _case(K, "sahur", "Сахур", 2, CaseTheme("wood", "stars", ("#4150c4", "#141a4d"), "#9fb0ff"),
          ["Tung Tung Tung Sahur", "Ta Ta Ta Ta Sahur", "Tric Trac Baraboom", "Bandito Bobritto", "Brr Brr Patapim",
           "Svinina Bombardino", "Talpa Di Fero", "Tim Cheese", "Noobini Pizzanini"]),
    _case(K, "crocodilo", "Крокодило", 3, CaseTheme("junk", "smoke", ("#66823e", "#26341a"), "#b4e06a"),
          ["La Grande Combinasion", "Bombombini Gusini", "Bombardiro Crocodilo", "Frigo Camelo", "Rhino Toasterino",
           "Glorbo Fruttodrillo", "Cacto Hipopotamo", "Trippi Troppi", "Gangster Footera", "Pipi Kiwi"]),
    _case(K, "sixseven", "67", 4, CaseTheme("coins", "lightning", ("#2f74dc", "#163a7e"), "#ffe14d"),
          ["67", "Chicleteira Bicicleteira", "Los Tralaleritos", "La Vacca Saturno Saturnita", "Burbaloni Loliloli",
           "Ballerina Cappuccina", "Chimpanzini Bananini", "Trulimero Trulicina", "Cappuccino Assassino",
           "Boneca Ambalabu", "Cacto Hipopotamo"]),
    _case(K, "secret", "Секретный", 5, CaseTheme("coins", "sparkle", ("#2b2b35", "#0d0d12"), "#f2f2f7"),
          ["Garama and Madundung", "Cash or Card", "67", "La Grande Combinasion", "Chicleteira Bicicleteira",
           "Tung Tung Tung Sahur", "Los Tralaleritos", "La Vacca Saturno Saturnita", "Bombombini Gusini",
           "Rhino Toasterino", "Glorbo Fruttodrillo"]),
    _case(K, "capitano", "Капитан", 6, CaseTheme("water", "bubbles", ("#2a92a6", "#0e3c48"), "#6ff4ff"),
          ["Fishino Clownino", "Moby Bros", "Jelly Moby", "Capitano Moby", "Cash or Card", "Garama and Madundung",
           "67", "La Grande Combinasion", "Los Tralaleritos", "La Vacca Saturno Saturnita"]),
    _case(K, "dragon", "Драгон", 7, CaseTheme("noodles", "fire", ("#a0703a", "#4a2c10"), "#ff8a1f"),
          ["Dragon Cannelloni", "Cerberus", "Celestial Pegasus", "Popcuru and Fizzuru", "Burguro And Fryuro",
           "Garama and Madundung", "67", "Tung Tung Tung Sahur", "Los Tralaleritos", "La Vacca Saturno Saturnita"]),
    _case(K, "fastfood", "Фастфуд", 8, CaseTheme("food", "sparkle", ("#d8402f", "#7a1a12"), "#ffb23d"),
          ["La Food Combinasion", "Popcuru and Fizzuru", "Pizza and Ranch", "Burguro And Fryuro", "Cash or Card",
           "Garama and Madundung", "67", "La Grande Combinasion", "Chicleteira Bicicleteira",
           "Tung Tung Tung Sahur", "La Vacca Saturno Saturnita"]),
    _case(K, "boo", "Бу!", 9, CaseTheme("pumpkins", "smoke", ("#5d3894", "#231238"), "#ff9a2e"),
          ["La Casa Boo", "Foxini Lanternini", "Dug dug dug", "Duggy Bros", "Cerberus", "Spooky and Pumpky",
           "Garama and Madundung", "67", "Los Tralaleritos", "La Vacca Saturno Saturnita"]),
    _case(K, "techno", "Техно", 10, CaseTheme("bolts", "lightning", ("#4c5d72", "#19212d"), "#3de0ff"),
          ["Digi Narwhal", "Bumbatron", "Venuspino", "Quackini Snackini", "Globa Steppa", "Cash or Card",
           "Garama and Madundung", "67", "Tung Tung Tung Sahur", "Chicleteira Bicicleteira"]),
    _case(K, "safe", "Сейф", 11, CaseTheme("bills", "sparkle", ("#cda33c", "#6a4f10"), "#ffe07a"),
          ["Rico Dinero", "Los Secret Combinasionas", "Los Sekolahs", "Fortunu and Cashuru", "Los Amigos",
           "Cash or Card", "Garama and Madundung", "67", "La Grande Combinasion", "Chicleteira Bicicleteira"]),
    _case(K, "griffin", "Грифон", 12, CaseTheme("embers", "fire", ("#8e1d1d", "#2a0606"), "#ff3b2f"),
          ["Griffin", "Dragon Gingerini", "Hydra Dragon Cannelloni", "Dragon Cannelloni", "Cerberus",
           "Celestial Pegasus", "Spooky and Pumpky", "Garama and Madundung", "67"]),
    _case(K, "sweet", "Сладкий", 13, CaseTheme("candy", "sparkle", ("#f1e7e1", "#b8423a"), "#ff6b6b"),
          ["Ginger Gerat", "Sammyni Cakini", "Pancake and Syrup", "La Breakfast Combinasion", "Cooki and Milki",
           "Fragrama and Chocrama", "Popcuru and Fizzuru", "Burguro And Fryuro", "Garama and Madundung", "67"]),
    _case(K, "party", "Праздник", 14, CaseTheme("gifts", "confetti", ("#e0508f", "#7a1846"), "#ffd1e6"),
          ["Kalika Bros", "Hydra Bunny", "Bunny and Eggy", "Rosey and Teddy", "Reinito Sleighito", "Sammyni Fattini",
           "Cooki and Milki", "Fragrama and Chocrama", "La Food Combinasion", "Pizza and Ranch",
           "Garama and Madundung"]),
    _case(K, "crystal", "Кристальный", 15, CaseTheme("crystals", "crystal", ("#b7a1de", "#5e4a8f"), "#e2d6ff"),
          ["Dragon Aquanini", "Kraken", "La Supreme Combinasion", "Tirilikalika Tirilikalako",
           "Hydra Dragon Cannelloni", "Dragon Cannelloni", "Los Sekolahs", "Reinito Sleighito", "Capitano Moby",
           "Celestial Pegasus", "Cash or Card"]),
    _case(K, "legend", "Легенда", 16, CaseTheme("coins", "fire", ("#ffcb3d", "#8a5a00"), "#fff0a8"),
          ["Antonio", "Dragon Gingerini", "Kalika Bros", "Fishino Clownino", "La Supreme Combinasion", "Hydra Bunny",
           "Dragon Cannelloni", "La Casa Boo", "Rico Dinero", "Los Sekolahs", "Fortunu and Cashuru"]),
    # ------------------------------------------------------------ ALL-IN
    _case(A, "phantom", "Фантомный", 1, CaseTheme("smoke", "smoke", ("#3c3f47", "#131418"), "#d4dbea"),
          ["Meowl", "Skibidi Toilet", "Love Love Bear", "Griffin", "Antonio", "Kalika Bros", "Digi Narwhal",
           "Hydra Dragon Cannelloni", "Dragon Cannelloni"]),
    _case(A, "frigo", "Фриго", 2, CaseTheme("snow", "snow", ("#a3d6f2", "#3a6f8f"), "#e8f8ff"),
          ["Elefanto Frigo", "Arcadragon", "Love Love Bear", "Antonio", "Dragon Gingerini", "Fishino Clownino",
           "La Supreme Combinasion", "Ginger Gerat", "Dragon Cannelloni"]),
    _case(A, "strawberry", "Клубничный", 3, CaseTheme("strawberries", "leaves", ("#e8384a", "#7a0f1c"), "#ff9aa8"),
          ["Strawberry Elephant", "Signore Carapace", "John Pork", "Meowl", "Skibidi Toilet", "Elefanto Frigo",
           "Antonio", "Kalika Bros", "Dragon Aquanini"]),
]

SEED_CASES_BY_CODE: dict[str, SeedCase] = {c.code: c for c in SEED_CASES}
