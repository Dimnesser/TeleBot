"""Каталог кейсов BrainCore.

Как на референсе пользователя: во всех кейсах только Secret/OG (дешёвые
кейсы — из дешёвых Secret), у каждого кейса — 3D-модель с героями внутри
(webapp/static/assets/cases/<code>.webp, рендер tools/case_renders).
Содержимое — только реальные персонажи Steal a Brainrot из
bot.data.brainrot_roster; в бесплатных кейсах ещё и монеты.

В платных кейсах — только брейнроты: из каталога пополнения (от 41 B, их
можно вывести из стока), а мелкий дроп — самые дешёвые брейнроты игры
(67, La Grande Combinasion … Lavadorito Spinito, 5–31 B). Монеты B —
только в бесплатном и реферальном кейсах.

Баланс (вся выводится из данных, руками не проставлено ничего):
  * ценность предмета — его ценность в B со скриншотов пользователя
    (brainrot_roster.ROSTER);
  * платный кейс окупается в PAYBACK_TARGET (~22%; для раскрута ~32%,
    жёсткие ~12%) открытий: вероятность делится между «окупающими» (ценность ≥ цены) и
    остальными, внутри групп шанс ∝ 1 / ценность^0.8 — дорогие реже;
  * цена = средний дроп / TARGET_RTP, округлённая вверх — кейс возвращает
    в среднем 90% цены; топ кейса выпадает в 0.5–8% открытий;
  * бесплатный кейс — натуральные веса 1/ценность^0.8, в среднем ≈ цене
    самого дешёвого кейса «Старт»: с него реально подняться.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from bot.data.brainrot_roster import ROSTER_BY_NAME
from bot.data.coins import COIN_RARITY, coin_name
from bot.database.models import CaseCategory
from bot.services.cases_service import CASE_WEIGHT_EXPONENT

CASES_CONTENT_VERSION = "27-no-coins"

TARGET_RTP = 0.90
PAYBACK_TARGET = 0.22
PAYBACK_BAND = (0.10, 0.40)
EASY_PAYBACK = 0.32  # кейсы «для раскрута»
HARD_PAYBACK = 0.12  # жёсткие дорогие: окупаются редко, зато ×6–×15
TOP_CHANCE_BAND = (0.005, 0.08)


@dataclass(frozen=True)
class SeedCaseItem:
    name: str
    value: int
    rarity: str | None = None
    weight: float | None = None  # доля выпадения; None — 1/ценность^k


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


def balanced_weights(values: list[int], target: float = PAYBACK_TARGET) -> tuple[list[float], int]:
    """Веса и цена платного кейса: окупается в ~PAYBACK_TARGET открытий,
    возвращает TARGET_RTP цены, топ в TOP_CHANCE_BAND. Перебирает порог
    «окупающих» предметов и их суммарную долю, берёт лучший вариант
    (ближе к цели и к натуральной цене)."""
    natural = price_for(values)
    best = None
    lo, hi = PAYBACK_BAND
    top = max(values)
    for threshold in sorted(set(values))[1:]:
        up = [i for i, v in enumerate(values) if v >= threshold]
        down = [i for i, v in enumerate(values) if v < threshold]
        w_up = sum(values[i] ** -CASE_WEIGHT_EXPONENT for i in up)
        w_down = sum(values[i] ** -CASE_WEIGHT_EXPONENT for i in down)
        for q100 in range(round(lo * 100), round(hi * 100) + 1):
            q = q100 / 100
            weights = [
                (q / w_up if i in up else (1 - q) / w_down) * v ** -CASE_WEIGHT_EXPONENT
                for i, v in enumerate(values)
            ]
            price = math.ceil(sum(v * w for v, w in zip(values, weights)) / TARGET_RTP)
            payback = sum(w for v, w in zip(values, weights) if v >= price)
            if not lo <= payback <= hi:
                continue
            top_chance = weights[values.index(top)]
            score = (abs(payback - target) * 4 + abs(math.log(price / natural))
                     + (0 if TOP_CHANCE_BAND[0] <= top_chance <= TOP_CHANCE_BAND[1] else 5))
            if best is None or score < best[0]:
                best = (score, weights, price)
    if best is None:
        raise ValueError(f"Кейс не балансируется: {values}")
    return best[1], best[2]


def _pool(names: list[str | int]) -> tuple[SeedCaseItem, ...]:
    """Имена брейнротов из ростера; число N — N B монетами (сразу на баланс)."""
    items = [
        SeedCaseItem(coin_name(n), n, COIN_RARITY) if isinstance(n, int)
        else SeedCaseItem(n, ROSTER_BY_NAME[n].value, ROSTER_BY_NAME[n].rarity.value)
        for n in names
    ]
    return tuple(sorted(items, key=lambda i: i.value, reverse=True))


CASE_THEMES: dict[str, CaseTheme] = {}


def _case(
    category: CaseCategory, code: str, name: str, sort_order: int, theme: CaseTheme, names: list[str | int],
    price: int | None = None, payback: float = PAYBACK_TARGET,
) -> SeedCase:
    """price=None — платный кейс, цена и веса из balanced_weights (payback —
    целевая доля окупающих открытий); иначе (бесплатный/реферальный) —
    натуральные веса и заданная цена."""
    items = _pool(names)
    CASE_THEMES[code] = theme
    if price is None:
        weights, price = balanced_weights([i.value for i in items], payback)
        items = tuple(SeedCaseItem(i.name, i.value, i.rarity, round(w, 6)) for i, w in zip(items, weights))
    return SeedCase(
        category=category,
        code=code,
        name=name,
        price_tokens=price,
        item_count_label=len(items),
        items=items,
        sort_order=sort_order,
    )


K, A = CaseCategory.STARTER, CaseCategory.APEX

GA, CC, BF = "Garama and Madundung", "Cash or Card", "Burguro And Fryuro"

SEED_CASES: list[SeedCase] = [
    # ------------------------------------------------------------ БЕСПЛАТНЫЕ
    # В среднем ≈ 16 B — почти цена «Старта»; 15% — брейнрот из каталога.
    _case(
        CaseCategory.FREE, "free", "Бесплатный", 1,
        CaseTheme("junk", "none", ("#a87a4c", "#5a3b1c"), "#e0b98a"),
        [3, 5, 8, 10, 15, GA, CC, BF, "Pizza and Ranch", "La Secret Combinasion", "Los Amigos"],
        price=0,
    ),
    # Не продаётся: открывается только бесплатными открытиями, которые
    # выдаёт партнёрский код (bot.services.partner_service).
    _case(
        CaseCategory.REFERRAL, "referral", "Реферальный", 2,
        CaseTheme("coins", "sparkle", ("#2c2c31", "#0c0c0f"), "#ffc93c"),
        [3, 5, 8, 12, 20, GA, CC, "Pizza and Ranch"],
        price=10,
    ),
    # ------------------------------------------------------------ КЕЙСЫ
    _case(K, "start", "Старт", 0, CaseTheme("coins", "dust", ("#4f8f5a", "#1c3a22"), "#b7ff8a"),
          ["67", "La Grande Combinasion", "Money Money Puggy", "Los Combinasionas", "Nuclearo Dinossauro", GA, CC]),
    _case(K, "mini", "Мини", 0, CaseTheme("coins", "dust", ("#6f7c8f", "#2a3240"), "#c9d6e8"),
          ["67", "La Grande Combinasion", "Money Money Puggy", "Nuclearo Dinossauro", GA, CC, BF, "Pizza and Ranch", "Los Amigos"]),
    _case(K, "kopeika", "Копейка", 0, CaseTheme("coins", "sparkle", ("#b98b3a", "#5a3f12"), "#ffd24d"),
          ["La Grande Combinasion", "Money Money Puggy", "Los Combinasionas", "Tang Tang Keletang", GA, CC, BF,
           "Popcuru and Fizzuru", "Fortunu and Cashuru"]),
    _case(K, "washer", "Стирка", 0, CaseTheme("water", "bubbles", ("#e8eef5", "#8497ad"), "#8fd8ff"),
          ["La Grande Combinasion", "Nuclearo Dinossauro", "Orcaledon", "Lavadorito Spinito", GA, CC, "Capitano Moby",
           "Celestial Pegasus", "Jelly Moby"]),
    _case(K, "sauce", "Соус", 0, CaseTheme("food", "fire", ("#d8b43a", "#8a2a12"), "#ff5a3a"),
          ["Money Money Puggy", "Nuclearo Dinossauro", "Tang Tang Keletang", "Ketupat Kepat", BF, "Pizza and Ranch", "Popcuru and Fizzuru", "La Food Combinasion",
           "Fragrama and Chocrama", "La Breakfast Combinasion"]),
    _case(K, "lasecret", "Ла Сикрет", 0, CaseTheme("bills", "lightning", ("#2a2a33", "#0b0b10"), "#f2f2f7"),
          ["Los Combinasionas", "La Grande Combinasion", "Tang Tang Keletang", "Lavadorito Spinito", GA, CC,
           "La Secret Combinasion", "La Food Combinasion", "Los Secret Combinasionas"]),
    _case(K, "tirili", "Тирили", 0, CaseTheme("coins", "lightning", ("#2f74dc", "#163a7e"), "#ffe14d"),
          ["Nuclearo Dinossauro", "Tang Tang Keletang", "Orcaledon", "Lavadorito Spinito", GA, BF, "Capitano Moby", "Celestial Pegasus", "Globa Steppa", "Tirilikalika Tirilikalako"]),
    _case(K, "safe", "Сейф", 0, CaseTheme("bills", "sparkle", ("#cda33c", "#6a4f10"), "#ffe07a"),
          ["Lavadorito Spinito", "Money Money Puggy", GA, CC, "Los Amigos", "Fortunu and Cashuru", "Los Sekolahs", "Los Secret Combinasionas", "Rico Dinero"]),
    _case(K, "boo", "Бу!", 0, CaseTheme("pumpkins", "smoke", ("#5d3894", "#231238"), "#ff9a2e"),
          ["Tang Tang Keletang", "Orcaledon", GA, "Spooky and Pumpky", "Cerberus", "Duggy Bros", "Dug dug dug", "Foxini Lanternini", "La Casa Boo"]),
    _case(K, "fastfood", "Фастфуд", 0, CaseTheme("food", "sparkle", ("#d8402f", "#7a1a12"), "#ffb23d"),
          ["Ketupat Kepat", "Lavadorito Spinito", BF, "Pizza and Ranch", "Popcuru and Fizzuru", "La Food Combinasion", "Fragrama and Chocrama",
           "Cooki and Milki", "La Breakfast Combinasion", "Pancake and Syrup", "Sammyni Cakini"]),
    # --- для лёгкого раскрута: только брейнроты каталога, без монет,
    # окупаются чаще (~38% открытий), множители умеренные (×3–×4).
    _case(K, "raskrut", "Раскрут", 0, CaseTheme("bills", "sparkle", ("#3a8f4f", "#123a1c"), "#9dff7a"),
          [GA, CC, BF, "Pizza and Ranch", "Popcuru and Fizzuru", "Capitano Moby", "Celestial Pegasus",
           "La Food Combinasion", "Fragrama and Chocrama", "Los Amigos"], payback=EASY_PAYBACK),
    _case(K, "double", "Дабл", 0, CaseTheme("coins", "lightning", ("#3f5fd8", "#14205a"), "#9fb4ff"),
          [BF, "Pizza and Ranch", "Capitano Moby", "La Food Combinasion", "Cooki and Milki", "Globa Steppa",
           "Los Amigos", "La Breakfast Combinasion", "Los Sekolahs", "Rico Dinero"], payback=EASY_PAYBACK),
    _case(K, "razgon", "Разгон", 0, CaseTheme("candy", "confetti", ("#d06ad8", "#4a1850"), "#ffb3f5"),
          ["Cooki and Milki", "Sammyni Fattini", "Spooky and Pumpky", "Cerberus", "Globa Steppa", "Reinito Sleighito",
           "Los Amigos", "Fortunu and Cashuru", "Quackini Snackini", "La Breakfast Combinasion", "Venuspino"],
          payback=EASY_PAYBACK),
    _case(K, "stairs", "Лесенка", 0, CaseTheme("wood", "dust", ("#b07a3a", "#4a2e10"), "#ffc27a"),
          ["Fragrama and Chocrama", "Cerberus", "Reinito Sleighito", "Quackini Snackini", "Duggy Bros", "Dug dug dug",
           "Ketupat Bros", "Bumbatron", "Dragon Cannelloni", "Jelly Moby", "Tirilikalika Tirilikalako"],
          payback=EASY_PAYBACK),
    _case(K, "ryvok", "Рывок", 0, CaseTheme("crystals", "lightning", ("#2fb3c8", "#0c3a44"), "#8ff4ff"),
          ["Los Secret Combinasionas", "Foxini Lanternini", "Rico Dinero", "Rosey and Teddy", "Bumbatron", "La Casa Boo",
           "Bunny and Eggy", "Dragon Cannelloni", "Pancake and Syrup", "Hydra Dragon Cannelloni", "Moby Bros",
           "Ginger Gerat"], payback=EASY_PAYBACK),
    _case(K, "turbo", "Турбо", 0, CaseTheme("embers", "lightning", ("#d8502f", "#5a1408"), "#ffb13b"),
          ["Rico Dinero", "La Casa Boo", "Bunny and Eggy", "Pancake and Syrup", "Sammyni Cakini", "Hydra Bunny",
           "Digi Narwhal", "La Supreme Combinasion", "Kraken", "Dragon Gingerini"], payback=EASY_PAYBACK),
    _case(K, "lucky", "Лаки", 0, CaseTheme("gifts", "sparkle", ("#2fa36b", "#0f3f28"), "#9dffc9"),
          [CC, "Fortunu and Cashuru", "Quackini Snackini", "Los Sekolahs", "Ketupat Bros", "Rosey and Teddy",
           "Bunny and Eggy", "Moby Bros", "Digi Narwhal"]),
    _case(K, "capitano", "Капитан", 0, CaseTheme("water", "bubbles", ("#2a92a6", "#0e3c48"), "#6ff4ff"),
          ["Orcaledon", "Tang Tang Keletang", CC, "Pizza and Ranch", "Capitano Moby", "Globa Steppa", "Bumbatron", "Jelly Moby", "Moby Bros",
           "Fishino Clownino"]),
    _case(K, "party", "Праздник", 0, CaseTheme("gifts", "confetti", ("#e0508f", "#7a1846"), "#ffd1e6"),
          ["La Food Combinasion", "Cooki and Milki", "Sammyni Fattini", "Reinito Sleighito", "Rosey and Teddy",
           "Bunny and Eggy", "Sammyni Cakini", "Hydra Bunny", "Kalika Bros"]),
    _case(K, "crystal", "Кристальный", 0, CaseTheme("crystals", "crystal", ("#b7a1de", "#5e4a8f"), "#e2d6ff"),
          ["Cerberus", "Spooky and Pumpky", "Globa Steppa", "Reinito Sleighito", "Los Sekolahs", "Dragon Cannelloni",
           "Hydra Dragon Cannelloni", "Tirilikalika Tirilikalako", "La Supreme Combinasion", "Kraken"]),
    _case(K, "dragon", "Драгон", 0, CaseTheme("noodles", "fire", ("#a0703a", "#4a2c10"), "#ff8a1f"),
          ["Celestial Pegasus", "Cerberus", "Globa Steppa", "Los Sekolahs", "Dragon Cannelloni", "Hydra Dragon Cannelloni",
           "Arcadragon", "Dragon Aquanini", "Dragon Gingerini"]),
    _case(K, "phantom", "Фантомный", 0, CaseTheme("smoke", "smoke", ("#3c3f47", "#131418"), "#d4dbea"),
          ["Los Amigos", "Fortunu and Cashuru", "Los Sekolahs", "Duggy Bros", "Foxini Lanternini", "La Casa Boo",
           "Hydra Dragon Cannelloni", "Digi Narwhal", "Griffin"]),
    _case(K, "legend", "Легенда", 0, CaseTheme("embers", "fire", ("#8e1d1d", "#2a0606"), "#ff3b2f"),
          ["Los Sekolahs", "Rico Dinero", "La Casa Boo", "Dragon Cannelloni", "Hydra Bunny", "La Supreme Combinasion",
           "Fishino Clownino", "Kalika Bros", "Dragon Gingerini", "Antonio"]),
    _case(K, "kraken", "Океан", 0, CaseTheme("water", "bubbles", ("#1c6f8a", "#08283a"), "#5dfff0"),
          ["Moby Bros", "Tirilikalika Tirilikalako", "Hydra Bunny", "Ginger Gerat", "Digi Narwhal",
           "La Supreme Combinasion", "Fishino Clownino", "Kraken", "Kalika Bros", "Dragon Aquanini"]),
    # ------------------------------------------------------------ ALL-IN
    _case(A, "frigo", "Фриго", 0, CaseTheme("snow", "snow", ("#a3d6f2", "#3a6f8f"), "#e8f8ff"),
          ["Dragon Cannelloni", "Ginger Gerat", "La Supreme Combinasion", "Fishino Clownino", "Dragon Gingerini",
           "Antonio", "Love Love Bear", "Arcadragon", "Elefanto Frigo"]),
    _case(A, "antonio", "Любовь", 0, CaseTheme("embers", "fire", ("#3a3a44", "#111116"), "#ffb13b"),
          ["La Supreme Combinasion", "Fishino Clownino", "Kraken", "Kalika Bros", "Dragon Aquanini", "Dragon Gingerini",
           "Antonio", "Griffin", "Love Love Bear"]),
    _case(A, "og", "OG", 0, CaseTheme("coins", "sparkle", ("#6a1f8f", "#2a0838"), "#ffd84d"),
          ["Tirilikalika Tirilikalako", "Digi Narwhal", "Kalika Bros", "Antonio", "Griffin", "Love Love Bear",
           "John Pork", "Skibidi Toilet", "Meowl"]),
    _case(A, "arca", "Мяу", 0, CaseTheme("crystals", "crystal", ("#7a4dff", "#2a1266"), "#d8c8ff"),
          ["Antonio", "Griffin", "Love Love Bear", "Arcadragon", "Elefanto Frigo", "Skibidi Toilet", "John Pork", "Meowl"]),
    _case(A, "strawberry", "Клубничный", 0, CaseTheme("strawberries", "leaves", ("#e8384a", "#7a0f1c"), "#ff9aa8"),
          ["Dragon Aquanini", "Kalika Bros", "Antonio", "Elefanto Frigo", "Skibidi Toilet", "Meowl", "John Pork",
           "Signore Carapace", "Strawberry Elephant"]),
    _case(A, "highroller", "Хайроллер", 0, CaseTheme("bills", "lightning", ("#1d1d24", "#050507"), "#ffd84d"),
          ["Kalika Bros", "Antonio", "Love Love Bear", "Elefanto Frigo", "Meowl", "Signore Carapace",
           "Strawberry Elephant"]),
    # --- жёсткие: окупаются ~в 12% открытий, но топ даёт ×6–×15
    _case(A, "chaos", "Хаос", 0, CaseTheme("smoke", "lightning", ("#5a2a8f", "#12061f"), "#d08cff"),
          ["Jelly Moby", "Sammyni Cakini", "Tirilikalika Tirilikalako", "Digi Narwhal", "Kraken", "Dragon Gingerini",
           "Love Love Bear", "Elefanto Frigo", "John Pork", "Signore Carapace"],
          payback=HARD_PAYBACK),
    _case(A, "hell", "Ад", 0, CaseTheme("embers", "fire", ("#b0201a", "#2a0402"), "#ff5a2a"),
          ["Dragon Cannelloni", "Hydra Dragon Cannelloni", "Moby Bros", "Ginger Gerat", "Fishino Clownino", "Kraken",
           "Antonio", "Love Love Bear", "Meowl", "Signore Carapace", "Strawberry Elephant"], payback=HARD_PAYBACK),
    _case(A, "abyss", "Бездна", 0, CaseTheme("water", "smoke", ("#15204a", "#03050f"), "#4d7bff"),
          ["Kraken", "Kalika Bros", "Dragon Aquanini", "Dragon Gingerini", "Antonio", "Griffin", "Love Love Bear",
           "Arcadragon", "Skibidi Toilet", "John Pork", "Meowl", "Signore Carapace", "Strawberry Elephant"],
          payback=HARD_PAYBACK),
    # --- мощные: дорогой вход, топ — Strawberry Elephant; Титан — самый дорогой кейс
    _case(A, "jackpot", "Джекпот", 0, CaseTheme("coins", "fire", ("#f0b429", "#6a3a00"), "#ffe27a"),
          ["Digi Narwhal", "La Supreme Combinasion", "Fishino Clownino", "Kraken", "Kalika Bros", "Dragon Aquanini",
           "Dragon Gingerini", "Antonio", "Love Love Bear", "Meowl", "Signore Carapace", "Strawberry Elephant"]),
    _case(A, "titan", "Титан", 0, CaseTheme("bolts", "lightning", ("#6a7384", "#15181f"), "#c9e4ff"),
          ["Love Love Bear", "Arcadragon", "Elefanto Frigo", "Skibidi Toilet", "John Pork", "Meowl", "Signore Carapace",
           "Strawberry Elephant"]),
    _case(A, "crown", "Корона", 0, CaseTheme("coins", "sparkle", ("#e9c24a", "#6b4c00"), "#fff2a8"),
          ["Griffin", "Love Love Bear", "Arcadragon", "Elefanto Frigo", "Skibidi Toilet", "John Pork", "Meowl",
           "Signore Carapace", "Strawberry Elephant"]),
]

# Внутри раздела кейсы идут лестницей цен — sort_order по возрастанию цены.
for _cat in {c.category for c in SEED_CASES}:
    _ordered = sorted((c for c in SEED_CASES if c.category == _cat), key=lambda c: (c.price_tokens or 0, c.code))
    for _n, _c in enumerate(_ordered, start=1):
        object.__setattr__(_c, "sort_order", _n)

SEED_CASES_BY_CODE: dict[str, SeedCase] = {c.code: c for c in SEED_CASES}
