"""Каталог кейсов Brainrot Battle.

Кейсы — собственный продукт этого бота: названия, темы и оформление
придуманы здесь и ничего не копируют у других сайтов. Содержимое кейсов —
только реальные персонажи Steal a Brainrot тиров Secret и OG из
bot.data.brainrot_roster (со скриншотов пользователя, сверены с вики).

Логика кейса (вся выводится из данных, руками не проставлено ничего):
  * ценность предмета 🎫 — его ценность в B со скриншотов пользователя
    (brainrot_roster.ROSTER);
  * шанс предмета ∝ 1 / ценность — каждый предмет вносит в средний дроп
    одинаковый вклад, поэтому дорогие персонажи редкие ровно настолько,
    насколько они дорогие (bot.services.cases_service.item_weight);
  * цена кейса = средний дроп / TARGET_RTP, округлённая вверх — кейс
    возвращает в среднем 90% своей цены, как и продажа предмета (SELL_RATE).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from bot.data.brainrot_roster import ROSTER_BY_NAME
from bot.database.models import CaseCategory

CASES_CONTENT_VERSION = "9-chest-models"

TARGET_RTP = 0.9


@dataclass(frozen=True)
class SeedCaseItem:
    name: str
    value: int
    rarity: str | None = None


@dataclass(frozen=True)
class CaseTheme:
    """Визуальная идентичность кейса — рисуется фронтендом (webapp/static/js/case-themes.js)."""

    tagline: str
    lore: str
    shape: str  # скин модели кейса-сундука: crate | crypt | hazmat | vault | forge | sunken | gift | royal
    particles: str  # эффект сцены: steam | bubbles | beats | wisps | sparks | dust | embers | prism
    colors: tuple[str, str, str]  # основной, акцент, глубина фона


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
    """Средний дроп при весах 1/value: n / Σ(1/v) (гармоническое среднее)."""
    return len(values) / sum(1 / v for v in values)


def price_for(values: list[int]) -> int:
    return math.ceil(expected_value(values) / TARGET_RTP)


def _pool(names: list[str]) -> tuple[SeedCaseItem, ...]:
    entries = sorted((ROSTER_BY_NAME[n] for n in names), key=lambda b: b.value, reverse=True)
    return tuple(SeedCaseItem(b.name, b.value, b.rarity.value) for b in entries)


CASE_THEMES: dict[str, CaseTheme] = {}


def _case(
    category: CaseCategory, code: str, name: str, sort_order: int, theme: CaseTheme, names: list[str]
) -> SeedCase:
    items = _pool(names)
    CASE_THEMES[code] = theme
    return SeedCase(
        category=category,
        code=code,
        name=name,
        price_tokens=price_for([i.value for i in items]),
        item_count_label=len(items),
        items=items,
        sort_order=sort_order,
    )


SEED_CASES: list[SeedCase] = [
    # ------------------------------------------------------------ СТАРТ
    _case(
        CaseCategory.STARTER, "nonna_kitchen", "Кухня Нонны", 1,
        CaseTheme(
            tagline="Фастфуд, десерты и Ginger Gerat на дне кастрюли",
            lore="Вся еда Secret-тира: бургеры, пицца, попкорн, панкейки и торт Sammyni Cakini.",
            shape="crate", particles="steam", colors=("#ff5a3c", "#ffd36b", "#2a0d08"),
        ),
        ["Burguro And Fryuro", "Pizza and Ranch", "Popcuru and Fizzuru", "La Food Combinasion",
         "Fragrama and Chocrama", "Cooki and Milki", "Quackini Snackini", "La Breakfast Combinasion",
         "Pancake and Syrup", "Sammyni Cakini", "Ginger Gerat"],
    ),
    _case(
        CaseCategory.STARTER, "ghost_lantern", "Фонарь Призраков", 2,
        CaseTheme(
            tagline="В La Casa Boo снова горит свет",
            lore="Хэллоуинская ночь: La Casa Boo, Spooky and Pumpky, Foxini Lanternini и Cerberus у ворот.",
            shape="crypt", particles="wisps", colors=("#b86bff", "#ff7ad9", "#12061f"),
        ),
        ["Garama and Madundung", "Spooky and Pumpky", "Cerberus", "Duggy Bros", "Dug dug dug",
         "Foxini Lanternini", "Venuspino", "La Casa Boo"],
    ),
    _case(
        CaseCategory.STARTER, "hybrid_lab", "Гибрид-Лаб", 3,
        CaseTheme(
            tagline="Скрещено. Не проверено. Elefanto Frigo сбежал.",
            lore="Техника, растения и роботы: Bumbatron, Digi Narwhal, Venuspino и холодильник-слон.",
            shape="hazmat", particles="bubbles", colors=("#7dff4a", "#18e0c8", "#06170c"),
        ),
        ["Cash or Card", "Globa Steppa", "Quackini Snackini", "Venuspino", "Bumbatron",
         "Tirilikalika Tirilikalako", "Digi Narwhal", "Elefanto Frigo"],
    ),
    # ------------------------------------------------------------ ЛЕГЕНДЫ
    _case(
        CaseCategory.SIGNATURE, "combo_vault", "Сейф Комбинасьон", 1,
        CaseTheme(
            tagline="Код от сейфа — удача",
            lore="Деньги и банды: Rico Dinero, Fortunu and Cashuru, Los Secret Combinasionas. За последней дверью — Antonio.",
            shape="vault", particles="dust", colors=("#ffc94a", "#fff1b8", "#150f02"),
        ),
        ["Cash or Card", "Globa Steppa", "Los Amigos", "Fortunu and Cashuru", "Los Sekolahs",
         "Los Secret Combinasionas", "Rico Dinero", "Ketupat Bros", "Tirilikalika Tirilikalako",
         "La Supreme Combinasion", "Antonio"],
    ),
    _case(
        CaseCategory.SIGNATURE, "dragon_forge", "Драконья Кузня", 2,
        CaseTheme(
            tagline="Куётся в огне. Выпадает в пламени.",
            lore="Крылатые и огнедышащие: все драконы-каннеллони, Griffin и Arcadragon на наковальне.",
            shape="forge", particles="embers", colors=("#ff3d1f", "#ffb02e", "#1a0400"),
        ),
        ["Celestial Pegasus", "Cerberus", "Dragon Cannelloni", "Hydra Dragon Cannelloni",
         "Dragon Aquanini", "Dragon Gingerini", "Griffin", "Arcadragon"],
    ),
    _case(
        CaseCategory.SIGNATURE, "abyss_dive", "Бездна", 3,
        CaseTheme(
            tagline="Шесть морских секретов. Kraken не спит.",
            lore="Спуск на дно: Capitano Moby, Jelly Moby, Moby Bros, Digi Narwhal и Fishino Clownino.",
            shape="sunken", particles="bubbles", colors=("#1fb6ff", "#5dfff0", "#020c1f"),
        ),
        ["Capitano Moby", "Jelly Moby", "Moby Bros", "Digi Narwhal", "Fishino Clownino", "Kraken"],
    ),
    _case(
        CaseCategory.SIGNATURE, "party_popper", "Хлопушка", 4,
        CaseTheme(
            tagline="Праздник каждый день. Love Love Bear — в конфетти.",
            lore="Все праздники Steal a Brainrot: день рождения, Рождество, Пасха и День святого Валентина.",
            shape="gift", particles="confetti", colors=("#ff4f8b", "#4fe3ff", "#1a0612"),
        ),
        ["Sammyni Fattini", "Reinito Sleighito", "Rosey and Teddy", "Bunny and Eggy",
         "Sammyni Cakini", "Hydra Bunny", "Kalika Bros", "Love Love Bear"],
    ),
    # ------------------------------------------------------------ ВЕРШИНА
    _case(
        CaseCategory.APEX, "og_throne", "Трон OG", 1,
        CaseTheme(
            tagline="Четыре короны. Один трон.",
            lore="Единственный кейс с OG-тиром: Skibidi Toilet, John Pork, Meowl и Strawberry Elephant.",
            shape="royal", particles="prism", colors=("#ff4fd8", "#ffd84d", "#10061a"),
        ),
        ["Antonio", "Griffin", "Love Love Bear", "Arcadragon", "Elefanto Frigo", "Skibidi Toilet",
         "John Pork", "Meowl", "Signore Carapace", "Strawberry Elephant"],
    ),
]

SEED_CASES_BY_CODE: dict[str, SeedCase] = {c.code: c for c in SEED_CASES}
