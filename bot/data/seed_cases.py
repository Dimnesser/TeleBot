"""Каталог кейсов BrainCore.

Кейсы — собственный продукт этого бота: названия, темы и оформление
придуманы здесь и ничего не копируют у других сайтов. Содержимое кейсов —
только реальные персонажи Steal a Brainrot тиров Secret и OG из
bot.data.brainrot_roster (со скриншотов пользователя, сверены с вики).

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
from bot.data.market import COLD_DEMAND, HOT_DEMAND, names_in_tiers, names_with_demand
from bot.database.models import CaseCategory
from bot.services.cases_service import CASE_WEIGHT_EXPONENT

CASES_CONTENT_VERSION = "13-market"

TARGET_RTP = 0.6


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
    shape: str  # скин модели кейса-сундука (webapp/static/js/case-themes.js, SKINS)
    particles: str  # эффект сцены: steam | bubbles | beats | wisps | sparks | dust | embers | prism
    colors: tuple[str, str, str]  # основной, акцент, глубина фона
    badge: str = ""  # рыночный ярлык на карточке (ХАЙП, T0, НЕЛИКВИД…), из bot.data.market


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


SEED_CASES: list[SeedCase] = [
    # ------------------------------------------------------------ РЫНОК
    # Пулы собраны не вручную, а из рыночного среза bot.data.market: спрос
    # (game.guide) и тир-лист трейдеров (tradekitsune) на MARKET_SNAPSHOT_DATE.
    _case(
        CaseCategory.STARTER, "market_hype", "Хайп", 1,
        CaseTheme(
            tagline="Самый высокий спрос на рынке",
            lore="Брейнроты со спросом Very High и High: их берут первыми.",
            shape="hype", particles="embers", colors=("#ff5b3a", "#ffc14d", "#1a0703"), badge="ХАЙП",
        ),
        names_with_demand(HOT_DEMAND),
    ),
    _case(
        CaseCategory.STARTER, "market_blue_chips", "Голубые фишки", 2,
        CaseTheme(
            tagline="Весь T0 тир-листа трейдеров",
            lore="Верхний тир трейдеров: от Burguro And Fryuro до Strawberry Elephant.",
            shape="chips", particles="prism", colors=("#4d8dff", "#b9d4ff", "#050c1f"), badge="T0",
        ),
        names_in_tiers("T0"),
    ),
    _case(
        CaseCategory.STARTER, "market_runners", "Ходовые", 3,
        CaseTheme(
            tagline="T1 и T2 — то, что крутится в трейдах",
            lore="Середина тир-листа: стабильные брейнроты без переплаты за хайп.",
            shape="runners", particles="sparks", colors=("#2fe3a0", "#c4ffe6", "#03140d"), badge="T1–T2",
        ),
        names_in_tiers("T1", "T2"),
    ),
    _case(
        CaseCategory.STARTER, "market_illiquid", "Неликвид", 4,
        CaseTheme(
            tagline="Спрос Very Low, ценность — настоящая",
            lore="Их редко просят в трейдах, но ценность в B у них настоящая: Meowl, Skibidi Toilet, Griffin.",
            shape="illiquid", particles="dust", colors=("#8aa0b8", "#e3ebf5", "#080c12"), badge="НЕЛИКВИД",
        ),
        names_with_demand(COLD_DEMAND),
    ),
    # ------------------------------------------------------------ ТЕМАТИЧЕСКИЕ
    _case(
        CaseCategory.SIGNATURE, "nonna_kitchen", "Кухня Нонны", 1,
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
        CaseCategory.SIGNATURE, "ghost_lantern", "Фонарь Призраков", 2,
        CaseTheme(
            tagline="В La Casa Boo снова горит свет",
            lore="Хэллоуинская ночь: La Casa Boo, Spooky and Pumpky, Foxini Lanternini и Cerberus у ворот.",
            shape="crypt", particles="wisps", colors=("#b86bff", "#ff7ad9", "#12061f"),
        ),
        ["Garama and Madundung", "Spooky and Pumpky", "Cerberus", "Duggy Bros", "Dug dug dug",
         "Foxini Lanternini", "Venuspino", "La Casa Boo"],
    ),
    _case(
        CaseCategory.SIGNATURE, "hybrid_lab", "Гибрид-Лаб", 3,
        CaseTheme(
            tagline="Скрещено. Не проверено. Elefanto Frigo сбежал.",
            lore="Техника, растения и роботы: Bumbatron, Digi Narwhal, Venuspino и холодильник-слон.",
            shape="hazmat", particles="bubbles", colors=("#7dff4a", "#18e0c8", "#06170c"),
        ),
        ["Cash or Card", "Globa Steppa", "Quackini Snackini", "Venuspino", "Bumbatron",
         "Tirilikalika Tirilikalako", "Digi Narwhal", "Elefanto Frigo"],
    ),
    _case(
        CaseCategory.SIGNATURE, "combo_vault", "Сейф Комбинасьон", 4,
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
        CaseCategory.SIGNATURE, "dragon_forge", "Драконья Кузня", 5,
        CaseTheme(
            tagline="Куётся в огне. Выпадает в пламени.",
            lore="Крылатые и огнедышащие: все драконы-каннеллони, Griffin и Arcadragon на наковальне.",
            shape="forge", particles="embers", colors=("#ff3d1f", "#ffb02e", "#1a0400"),
        ),
        ["Celestial Pegasus", "Cerberus", "Dragon Cannelloni", "Hydra Dragon Cannelloni",
         "Dragon Aquanini", "Dragon Gingerini", "Griffin", "Arcadragon"],
    ),
    _case(
        CaseCategory.SIGNATURE, "abyss_dive", "Бездна", 6,
        CaseTheme(
            tagline="Шесть морских секретов. Kraken не спит.",
            lore="Спуск на дно: Capitano Moby, Jelly Moby, Moby Bros, Digi Narwhal и Fishino Clownino.",
            shape="sunken", particles="bubbles", colors=("#1fb6ff", "#5dfff0", "#020c1f"),
        ),
        ["Capitano Moby", "Jelly Moby", "Moby Bros", "Digi Narwhal", "Fishino Clownino", "Kraken"],
    ),
    _case(
        CaseCategory.SIGNATURE, "party_popper", "Хлопушка", 7,
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
    # ------------------------------------------------------------ БЕСПЛАТНЫЕ
    _case(
        CaseCategory.FREE, "free_handout", "Халява", 1,
        CaseTheme(
            tagline="Раз в 10 минут — бесплатно",
            lore="Пара монет или брейнрот из самых дешёвых. Копи, продавай и поднимайся выше.",
            shape="freebie", particles="dust", colors=("#8fd3ff", "#e6f6ff", "#07121c"),
        ),
        [1, 2, 3, 5, "Noobini Pizzanini", "Lirilì Larilà", "Tim Cheese", "Fluriflura"],
        price=0,
    ),
    # Не продаётся: открывается только бесплатными открытиями, которые
    # выдаёт партнёрский код (bot.services.partner_service).
    _case(
        CaseCategory.REFERRAL, "referral_gift", "Реферальный", 2,
        CaseTheme(
            tagline="Подарок за код партнёра",
            lore="Небольшой стартовый набор: монеты и простые брейнроты.",
            shape="partner", particles="dust", colors=("#c6ff3d", "#eaffb0", "#0b1206"),
        ),
        [3, 5, 10, "Noobini Pizzanini", "Tim Cheese", "Pipi Kiwi", "Trippi Troppi", "Boneca Ambalabu", "Brr Brr Patapim"],
    ),
    # ------------------------------------------------------------ ЭКОНОМ
    _case(
        CaseCategory.ECONOMY, "eco_cardboard", "Картонка", 1,
        CaseTheme(tagline="", lore="Коробка со склада: монетки и Common.",
                  shape="cardboard", particles="dust", colors=("#c89a5b", "#f3dcae", "#150e06")),
        [1, 2, 3, "Noobini Pizzanini", "Lirilì Larilà", "Tim Cheese", "Fluriflura"],
    ),
    _case(
        CaseCategory.ECONOMY, "eco_bin", "Мусорка", 2,
        CaseTheme(tagline="", lore="Кто-то выбросил — ты подобрал.",
                  shape="bin", particles="dust", colors=("#7fbf8e", "#d8f0de", "#08120b")),
        [2, 5, "Talpa Di Fero", "Svinina Bombardino", "Pipi Kiwi", "Trippi Troppi", "Gangster Footera"],
    ),
    _case(
        CaseCategory.ECONOMY, "eco_lunchbox", "Ланчбокс", 3,
        CaseTheme(tagline="", lore="Перекус: капучино, бананы и фруктовый крокодил.",
                  shape="lunchbox", particles="steam", colors=("#ff8a5c", "#ffe0c2", "#1a0b05")),
        ["Tim Cheese", "Pipi Kiwi", "Cappuccino Assassino", "Chimpanzini Bananini", "Ballerina Cappuccina", "Glorbo Fruttodrillo"],
    ),
    _case(
        CaseCategory.ECONOMY, "eco_toolbox", "Инструменты", 4,
        CaseTheme(tagline="", lore="Молотки, ключи и Bombardiro Crocodilo на дне.",
                  shape="toolbox", particles="sparks", colors=("#ff4d5e", "#ffd0d4", "#170506")),
        ["Talpa Di Fero", "Gangster Footera", "Bandito Bobritto", "Tric Trac Baraboom", "Brr Brr Patapim",
         "Rhino Toasterino", "Bombardiro Crocodilo"],
    ),
    _case(
        CaseCategory.ECONOMY, "eco_piggy", "Копилка", 5,
        CaseTheme(tagline="", lore="Монеты звенят. Иногда — La Vacca Saturno Saturnita.",
                  shape="piggy", particles="dust", colors=("#ff8fc7", "#ffe3f1", "#1a0712")),
        [3, 5, 10, 20, "Boneca Ambalabu", "Cacto Hipopotamo", "Bombombini Gusini", "La Vacca Saturno Saturnita"],
    ),
    _case(
        CaseCategory.ECONOMY, "eco_sahur", "Ночная смена", 6,
        CaseTheme(tagline="", lore="Вся семья Sahur и Tung Tung Tung Sahur за барабаном.",
                  shape="sahur", particles="wisps", colors=("#7b8cff", "#dfe3ff", "#070a1f")),
        ["Talpa Di Fero", "Svinina Bombardino", "Ta Ta Ta Ta Sahur", "Tric Trac Baraboom", "Tung Tung Tung Sahur"],
    ),
    _case(
        CaseCategory.ECONOMY, "eco_mystery", "Дно тир-листа", 7,
        CaseTheme(tagline="", lore="T4–T5 и Mythic из T7: шанс на La Grande Combinasion и 67.",
                  shape="mystery", particles="prism", colors=("#b58cff", "#efe4ff", "#0d0719"), badge="T4–T7"),
        ["Frigo Camelo", "Rhino Toasterino", "Bombardiro Crocodilo", "Bombombini Gusini"] + names_in_tiers("T4", "T5"),
    ),
    _case(
        CaseCategory.ECONOMY, "eco_first_secret", "Первый секрет", 8,
        CaseTheme(tagline="", lore="Самые дешёвые Secret рынка — мост от эконома к большим кейсам.",
                  shape="firstsecret", particles="sparks", colors=("#ffd84d", "#fff4c2", "#171002"), badge="SECRET"),
        ["La Vacca Saturno Saturnita", "Los Tralaleritos", "Tung Tung Tung Sahur", "Chicleteira Bicicleteira",
         "La Grande Combinasion", "67", "Garama and Madundung", "Cash or Card", "Burguro And Fryuro",
         "Pizza and Ranch", "Popcuru and Fizzuru", "Capitano Moby", "Celestial Pegasus", "La Food Combinasion"],
    ),
]

SEED_CASES_BY_CODE: dict[str, SeedCase] = {c.code: c for c in SEED_CASES}
