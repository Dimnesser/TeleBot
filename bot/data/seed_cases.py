"""Каталог кейсов BrainCore.

Как на референсе пользователя: во всех кейсах только Secret/OG (дешёвые
кейсы — из дешёвых Secret), у каждого кейса — 3D-модель с героями внутри
(webapp/static/assets/cases/<code>.webp, рендер tools/case_renders).
Содержимое — только реальные персонажи Steal a Brainrot из
bot.data.brainrot_roster; в бесплатных кейсах ещё и монеты.

Логика кейса (вся выводится из данных, руками не проставлено ничего):
  * ценность предмета 🎫 — его ценность в B со скриншотов пользователя
    (brainrot_roster.ROSTER);
  * шанс предмета ∝ 1 / ценность — дорогие брейнроты реже, но выпадают
    (bot.services.cases_service.item_weight);
  * цена кейса = средний дроп / TARGET_RTP, округлённая вверх — кейс
    возвращает в среднем 85% своей цены, окупается в 8–34% открытий.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from bot.data.brainrot_roster import ROSTER_BY_NAME
from bot.data.coins import COIN_RARITY, coin_name
from bot.database.models import CaseCategory
from bot.services.cases_service import CASE_WEIGHT_EXPONENT

CASES_CONTENT_VERSION = "18-free-like-reference"

TARGET_RTP = 0.85


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

# Самые дешёвые Secret — «дно» дешёвых кейсов, как на референсе.
CHEAP = ["67", "La Grande Combinasion", "Money Money Puggy", "Nuclearo Dinossauro", "Tang Tang Keletang",
         "Orcaledon", "Lavadorito Spinito", "Ventoliero Pavonero", "Ketchuru and Musturu", "Noodle Noodle Poodle"]

SEED_CASES: list[SeedCase] = [
    # ------------------------------------------------------------ БЕСПЛАТНЫЕ
    _case(
        CaseCategory.FREE, "free", "Бесплатный", 1,
        CaseTheme("junk", "none", ("#a87a4c", "#5a3b1c"), "#e0b98a"),
        # Ровно как бесплатный кейс на референсе пользователя (11 предметов).
        [2, 3, 5, "Los Combinasionas", "Nuclearo Dinossauro", "Ketupat Kepat", "Lavadorito Spinito",
         "Ventoliero Pavonero", "Cash or Card", "Ketchuru and Musturu", "La Secret Combinasion"],
        price=0,
    ),
    # Не продаётся: открывается только бесплатными открытиями, которые
    # выдаёт партнёрский код (bot.services.partner_service). Дроп мелкий.
    _case(
        CaseCategory.REFERRAL, "referral", "Реферальный", 2,
        CaseTheme("coins", "sparkle", ("#2c2c31", "#0c0c0f"), "#ffc93c"),
        [2, 3, 5, "67", "La Grande Combinasion", "Money Money Puggy", "Nuclearo Dinossauro", "Tang Tang Keletang",
         "Orcaledon"],
    ),
    # ------------------------------------------------------------ КЕЙСЫ
    _case(K, "tirili", "Тирили", 1, CaseTheme("coins", "lightning", ("#2f74dc", "#163a7e"), "#ffe14d"),
          ["Tirilikalika Tirilikalako", "Capitano Moby", "Burguro And Fryuro"] + CHEAP),
    _case(K, "capitano", "Капитан", 2, CaseTheme("water", "bubbles", ("#2a92a6", "#0e3c48"), "#6ff4ff"),
          ["Fishino Clownino", "Jelly Moby", "Capitano Moby", "Orcaledon", "Nuclearo Dinossauro", "Money Money Puggy",
           "La Grande Combinasion", "Tang Tang Keletang", "Lavadorito Spinito", "Noodle Noodle Poodle",
           "Ketchuru and Musturu"]),
    _case(K, "safe", "Сейф", 3, CaseTheme("bills", "sparkle", ("#cda33c", "#6a4f10"), "#ffe07a"),
          ["Rico Dinero", "Los Secret Combinasionas", "Los Sekolahs", "Fortunu and Cashuru", "Los Amigos",
           "Cash or Card", "Money Money Puggy", "Garama and Madundung", "Ventoliero Pavonero", "Tang Tang Keletang"]),
    _case(K, "boo", "Бу!", 4, CaseTheme("pumpkins", "smoke", ("#5d3894", "#231238"), "#ff9a2e"),
          ["La Casa Boo", "Foxini Lanternini", "Dug dug dug", "Duggy Bros", "Cerberus", "Spooky and Pumpky",
           "Garama and Madundung", "Tang Tang Keletang", "Orcaledon", "Lavadorito Spinito"]),
    _case(K, "fastfood", "Фастфуд", 5, CaseTheme("food", "sparkle", ("#d8402f", "#7a1a12"), "#ffb23d"),
          ["Sammyni Cakini", "Pancake and Syrup", "Cooki and Milki", "Fragrama and Chocrama", "La Food Combinasion",
           "Popcuru and Fizzuru", "Pizza and Ranch", "Burguro And Fryuro", "Ketchuru and Musturu",
           "Noodle Noodle Poodle", "Garama and Madundung"]),
    _case(K, "party", "Праздник", 6, CaseTheme("gifts", "confetti", ("#e0508f", "#7a1846"), "#ffd1e6"),
          ["Kalika Bros", "Hydra Bunny", "Bunny and Eggy", "Rosey and Teddy", "Reinito Sleighito", "Sammyni Fattini",
           "Cooki and Milki", "Fragrama and Chocrama", "La Food Combinasion"]),
    _case(K, "dragon", "Драгон", 7, CaseTheme("noodles", "fire", ("#a0703a", "#4a2c10"), "#ff8a1f"),
          ["Dragon Gingerini", "Dragon Aquanini", "Hydra Dragon Cannelloni", "Dragon Cannelloni", "Cerberus",
           "Celestial Pegasus", "Globa Steppa"]),
    _case(K, "crystal", "Кристальный", 8, CaseTheme("crystals", "crystal", ("#b7a1de", "#5e4a8f"), "#e2d6ff"),
          ["Kraken", "La Supreme Combinasion", "Tirilikalika Tirilikalako", "Hydra Dragon Cannelloni",
           "Dragon Cannelloni", "Los Sekolahs", "Reinito Sleighito", "Globa Steppa", "Spooky and Pumpky", "Cerberus"]),
    _case(K, "phantom", "Фантомный", 9, CaseTheme("smoke", "smoke", ("#3c3f47", "#131418"), "#d4dbea"),
          ["Griffin", "Digi Narwhal", "Hydra Dragon Cannelloni", "La Casa Boo", "Foxini Lanternini", "Duggy Bros",
           "Los Sekolahs", "Fortunu and Cashuru", "Los Amigos"]),
    _case(K, "legend", "Легенда", 10, CaseTheme("embers", "fire", ("#8e1d1d", "#2a0606"), "#ff3b2f"),
          ["Antonio", "Dragon Gingerini", "Kalika Bros", "Fishino Clownino", "La Supreme Combinasion", "Hydra Bunny",
           "Dragon Cannelloni", "La Casa Boo", "Rico Dinero", "Los Sekolahs"]),
    # ------------------------------------------------------------ ALL-IN
    _case(A, "frigo", "Фриго", 1, CaseTheme("snow", "snow", ("#a3d6f2", "#3a6f8f"), "#e8f8ff"),
          ["Elefanto Frigo", "Arcadragon", "Love Love Bear", "Antonio", "Dragon Gingerini", "Fishino Clownino",
           "La Supreme Combinasion", "Ginger Gerat", "Dragon Cannelloni"]),
    _case(A, "og", "OG", 2, CaseTheme("coins", "sparkle", ("#6a1f8f", "#2a0838"), "#ffd84d"),
          ["Meowl", "Skibidi Toilet", "John Pork", "Love Love Bear", "Griffin", "Antonio", "Kalika Bros",
           "Digi Narwhal", "Tirilikalika Tirilikalako"]),
    _case(A, "strawberry", "Клубничный", 3, CaseTheme("strawberries", "leaves", ("#e8384a", "#7a0f1c"), "#ff9aa8"),
          ["Strawberry Elephant", "Signore Carapace", "John Pork", "Meowl", "Skibidi Toilet", "Elefanto Frigo",
           "Antonio", "Kalika Bros", "Dragon Aquanini"]),
]

SEED_CASES_BY_CODE: dict[str, SeedCase] = {c.code: c for c in SEED_CASES}
