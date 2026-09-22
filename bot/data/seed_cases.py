"""Каталог кейсов и пулы дропа.

Форма каталога (category/code/name/price_tokens/item_count_label/note) —
[ПОДТВЕРЖДЕНО СКРИНШОТОМ] из разделов «КЕЙСЫ», «ТЕМАТИЧЕСКИЕ КЕЙСЫ»,
«ALL-IN», «ПАРТНЕРЫ», «БЕСПЛАТНЫЕ КЕЙСЫ». Где число на скриншоте было
обрезано — здесь стоит None, а не придуманное.

Содержимое кейсов (какие персонажи может выдать кейс) — два случая:
  1. «Драгон» и «Тако» — [ПОДТВЕРЖДЕНО СКРИНШОТОМ] «Что может выпасть»,
     имена и значения взяты буквально с экрана кейса, не тронуты.
  2. Все остальные кейсы — на скриншотах их дроп-пул не показан (кейс был
     виден только в каталоге как карточка). Раньше они были помечены
     is_openable=False. Теперь заполнены реальными персонажами из
     bot.data.brainrot_roster (настоящий ростер Steal a Brainrot,
     см. докстринг того модуля про источники) — детерминированно по seed
     кейса, смещено по редкости в сторону цены кейса (дорогой кейс — более
     редкие персонажи). Это не выдумка «Test Brainrot», а реальный контент
     игры, просто распределённый по кейсам самим ботом, а не скриншотом
     (интерфейс которого этого не показывал).
"""
from __future__ import annotations

import math
import random as _random
from dataclasses import dataclass, field

from bot.data.brainrot_roster import RARITY_DROP_WEIGHT, RARITY_ORDER, ROSTER, ROSTER_BY_RARITY, infer_rarity
from bot.database.models import CaseCategory

CASES_CONTENT_VERSION = "4-steal-a-brainrot-roster-best-rarity"


@dataclass(frozen=True)
class SeedCaseItem:
    name: str
    value: int
    rarity: str | None = None


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


def _center_index_for_price(price: int | None) -> float:
    """Дорогой кейс -> центр распределения смещён к редким тирам (индекс 0..6)."""
    if not price:
        return 0.5
    lo, hi = math.log(9), math.log(35000)
    t = (math.log(min(max(price, 9), 35000)) - lo) / (hi - lo)
    return t * (len(RARITY_ORDER) - 1)


def _generate_pool(case_code: str, price: int | None, count: int | None) -> tuple[SeedCaseItem, ...]:
    """Дешёвый кейс физически не может выдать топ-тир: тиры не просто менее
    вероятны, а вообще исключены из пула за пределами окна ±1 от центра
    (иначе 19-токенный кейс мог бы содержать OG-предмет на 50 000 —
    абсурдная экономика). Внутри окна веса всё равно берутся из
    RARITY_DROP_WEIGHT, так что нижний тир окна всё равно доминирует.
    """
    n = count or 8
    rng = _random.Random(f"sab::{case_code}")  # детерминированный seed — стабильно между переразвёртываниями
    center_i = round(_center_index_for_price(price))
    lo = max(0, center_i - 1)
    hi = min(len(RARITY_ORDER) - 1, center_i + 1)
    window = RARITY_ORDER[lo : hi + 1]
    window_weights = [RARITY_DROP_WEIGHT[r] for r in window]

    chosen: list = []
    seen_names: set[str] = set()
    attempts = 0
    max_attempts = n * 30
    while len(chosen) < min(n, sum(len(ROSTER_BY_RARITY[r]) for r in window)) and attempts < max_attempts:
        attempts += 1
        rarity = rng.choices(window, weights=window_weights, k=1)[0]
        candidates = [b for b in ROSTER_BY_RARITY[rarity] if b.name not in seen_names]
        if not candidates:
            continue
        pick = rng.choice(candidates)
        chosen.append(pick)
        seen_names.add(pick.name)

    chosen.sort(key=lambda b: b.demo_value, reverse=True)
    return tuple(SeedCaseItem(name=b.name, value=b.demo_value, rarity=b.rarity.value) for b in chosen)


# --- «Драгон» и «Тако»: буквально со скриншота «Что может выпасть» ---
_DRAGON_ITEMS = (
    SeedCaseItem("La Supreme Combinasion", 2704),
    SeedCaseItem("Moby Bros", 1604),
    SeedCaseItem("Dragon Cannelloni", 973),
    SeedCaseItem("La Casa Boo", 621),
    SeedCaseItem("Rosey and Teddy", 525),
    SeedCaseItem("Foxini Lanternini", 445),
    SeedCaseItem("Guest 666", 336),
)
_TAKO_ITEMS = (
    SeedCaseItem("Hydra Dragon Cannelloni", 1220),
    SeedCaseItem("La Casa Boo", 621),
    SeedCaseItem("Rosey and Teddy", 525),
    SeedCaseItem("Foxini Lanternini", 445),
    SeedCaseItem("Fortunu and Cashuru", 230),
    SeedCaseItem("Sammuni Fattini", 140),
)
_DRAGON_ITEMS = tuple(SeedCaseItem(i.name, i.value, infer_rarity(i.value).value) for i in _DRAGON_ITEMS)
_TAKO_ITEMS = tuple(SeedCaseItem(i.name, i.value, infer_rarity(i.value).value) for i in _TAKO_ITEMS)


def _case(category: CaseCategory, code: str, name: str, price: int | None, count: int | None, sort_order: int, note: str | None = None) -> SeedCase:
    return SeedCase(
        category, code, name, price, count, note=note, sort_order=sort_order,
        items=_generate_pool(code, price, count),
    )


SEED_CASES: list[SeedCase] = [
    # --- КЕЙСЫ ---
    SeedCase(CaseCategory.CASES, "cases_dragon", "Драгон", 500, 7, sort_order=1, items=_DRAGON_ITEMS),
    SeedCase(CaseCategory.CASES, "cases_tako", "Тако", 189, 11, sort_order=2, items=_TAKO_ITEMS),
    _case(CaseCategory.CASES, "cases_nubini", "Нубини", 19, 14, 3),
    _case(CaseCategory.CASES, "cases_lucky_block", "Лаки-Блок", 209, 14, 4),
    _case(CaseCategory.CASES, "cases_cerber", "Цербер", 117, 12, 5),
    _case(CaseCategory.CASES, "cases_strawberry", "Клубничный", 1679, 8, 6),
    _case(CaseCategory.CASES, "cases_six_seven", "Сикс Севен", 67, 10, 7),
    _case(CaseCategory.CASES, "cases_hirsy", "Гирсы", 17, 14, 8),

    # --- ТЕМАТИЧЕСКИЕ КЕЙСЫ ---
    _case(CaseCategory.THEMATIC, "thematic_newyear", "Новогодний", 169, 9, 1),
    _case(CaseCategory.THEMATIC, "thematic_seabros", "Морская братва", 119, 8, 2),
    _case(CaseCategory.THEMATIC, "thematic_summer", "Летний", 769, 8, 3),
    _case(CaseCategory.THEMATIC, "thematic_easter", "Пасхальный", 219, 9, 4),
    _case(CaseCategory.THEMATIC, "thematic_fuse", "Фьюз", 2390, 7, 5),
    _case(CaseCategory.THEMATIC, "thematic_traders", "Лос Трейдеры", 89, 12, 6),
    _case(CaseCategory.THEMATIC, "thematic_anniversary", "Юбилейный", None, 9, 7, note="Цена на скриншоте обрезана."),
    _case(CaseCategory.THEMATIC, "thematic_honey", "Медовый", None, 9, 8, note="Цена на скриншоте обрезана."),
    _case(CaseCategory.THEMATIC, "thematic_six_seven", "Сикс Севен", 67, 10, 9),
    _case(CaseCategory.THEMATIC, "thematic_hirsy", "Гирсы", 17, 14, 10),
    _case(CaseCategory.THEMATIC, "thematic_losy", "Лосы", 139, 14, 11),
    _case(CaseCategory.THEMATIC, "thematic_dlc", "ДЛС", 229, 9, 12),
    _case(CaseCategory.THEMATIC, "thematic_basic", "Базовый", 9, 9, 13),
    _case(CaseCategory.THEMATIC, "thematic_og", "ОГ", 10000, 10, 14),
    _case(CaseCategory.THEMATIC, "thematic_garama", "Гарама", 39, 10, 15),
    _case(CaseCategory.THEMATIC, "thematic_imperial", "Императорский", 34900, 11, 16),

    # --- ALL-IN ---
    _case(CaseCategory.ALLIN, "allin_skibidi", "Скибиди Алл-ин", 29, 4, 1),
    _case(CaseCategory.ALLIN, "allin_meowl", "Меовл Алл-ин", 39, 4, 2),
    _case(CaseCategory.ALLIN, "allin_pork", "Порк Алл-ин", 39, 4, 3),
    _case(CaseCategory.ALLIN, "allin_elephant", "Слон Алл-ин", 49, 4, 4),

    # --- ПАРТНЕРЫ ---
    _case(CaseCategory.PARTNERS, "partners_nikil", "Никил", 49, 9, 1),
    _case(CaseCategory.PARTNERS, "partners_lisharty", "Лишарти", None, 9, 2, note="Цена на скриншоте обрезана."),

    # --- БЕСПЛАТНЫЕ КЕЙСЫ --- (у большинства — особые условия открытия, не просто цена)
    _case(CaseCategory.FREE, "free_daily", "Бесплатный", None, 11, 1, note="Открывается бесплатно раз в сутки по таймеру (на скриншоте «через 5ч 08м»)."),
    _case(CaseCategory.FREE, "free_deposit", "За депозит", None, 12, 2, note="Условие открытия — сумма депозитов (на скриншоте «Осталось 194 B» до цели)."),
    _case(CaseCategory.FREE, "free_referral", "Реферальный", None, 9, 3, note="Разовый кейс за реферальную активность (на скриншоте уже был отмечен как «Уже забрано»)."),
    _case(CaseCategory.FREE, "free_crystal", "Кристальный", 109, 8, 4, note="Цена в 🎫."),
    _case(CaseCategory.FREE, "free_phantom", "Фантомный", 240, 9, 5, note="Цена в 🎫."),
    _case(CaseCategory.FREE, "free_staking", "За стейкинг", None, 18, 6, note="Условие открытия — активный стейк от 500 B (раздел «Бонусы»)."),
]
