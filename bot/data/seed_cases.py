"""Каталог кейсов и подтверждённые пулы дропа.

Все записи ниже — [ПОДТВЕРЖДЕНО СКРИНШОТОМ] названия/цены/«N предм.» из
разделов «КЕЙСЫ», «ТЕМАТИЧЕСКИЕ КЕЙСЫ», «ALL-IN», «ПАРТНЕРЫ», «БЕСПЛАТНЫЕ
КЕЙСЫ». Где число на скриншоте было обрезано (цена/кол-во не читается) —
здесь стоит None, а не придуманное число.

Открыть по-настоящему (со случайным дропом) можно только те кейсы, у
которых ITEMS не пуст и полностью совпадает по количеству с CASES[...].items
count — это «Драгон» (7 из 7 подтверждены) и частично «Тако» (6 из 11,
остальные 5 слотов со скриншота не видны). Все остальные кейсы каталога
перечислены для навигационной точности, но открытие для них помечено как
недоступное, пока не пришлют скриншот их «Что может выпасть».

Цена везде указана как есть с картинки, но единица переведена в демо-валюту
🎫 (game_tokens) — см. комментарий у bot.database.models.User.game_tokens.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from bot.database.models import CaseCategory


@dataclass(frozen=True)
class SeedCaseItem:
    name: str
    value: int


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


SEED_CASES: list[SeedCase] = [
    # --- КЕЙСЫ --- (полностью подтверждённые пулы: Драгон, частично Тако)
    SeedCase(
        CaseCategory.CASES, "cases_dragon", "Драгон", 500, 7, sort_order=1,
        items=(
            SeedCaseItem("La Supreme Combinasion", 2704),
            SeedCaseItem("Moby Bros", 1604),
            SeedCaseItem("Dragon Cannelloni", 973),
            SeedCaseItem("La Casa Boo", 621),
            SeedCaseItem("Rosey and Teddy", 525),
            SeedCaseItem("Foxini Lanternini", 445),
            SeedCaseItem("Guest 666", 336),
        ),
    ),
    SeedCase(
        CaseCategory.CASES, "cases_tako", "Тако", 189, 11, sort_order=2,
        items=(
            SeedCaseItem("Hydra Dragon Cannelloni", 1220),
            SeedCaseItem("La Casa Boo", 621),
            SeedCaseItem("Rosey and Teddy", 525),
            SeedCaseItem("Foxini Lanternini", 445),
            SeedCaseItem("Fortunu and Cashuru", 230),
            SeedCaseItem("Sammuni Fattini", 140),
        ),
    ),
    SeedCase(CaseCategory.CASES, "cases_nubini", "Нубини", 19, 14, sort_order=3),
    SeedCase(CaseCategory.CASES, "cases_lucky_block", "Лаки-Блок", 209, 14, sort_order=4),
    SeedCase(CaseCategory.CASES, "cases_cerber", "Цербер", 117, 12, sort_order=5),
    SeedCase(CaseCategory.CASES, "cases_strawberry", "Клубничный", 1679, 8, sort_order=6),
    SeedCase(CaseCategory.CASES, "cases_six_seven", "Сикс Севен", 67, 10, sort_order=7),
    SeedCase(CaseCategory.CASES, "cases_hirsy", "Гирсы", 17, 14, sort_order=8),

    # --- ТЕМАТИЧЕСКИЕ КЕЙСЫ ---
    SeedCase(CaseCategory.THEMATIC, "thematic_newyear", "Новогодний", 169, 9, sort_order=1),
    SeedCase(CaseCategory.THEMATIC, "thematic_seabros", "Морская братва", 119, 8, sort_order=2),
    SeedCase(CaseCategory.THEMATIC, "thematic_summer", "Летний", 769, 8, sort_order=3),
    SeedCase(CaseCategory.THEMATIC, "thematic_easter", "Пасхальный", 219, 9, sort_order=4),
    SeedCase(CaseCategory.THEMATIC, "thematic_fuse", "Фьюз", 2390, 7, sort_order=5),
    SeedCase(CaseCategory.THEMATIC, "thematic_traders", "Лос Трейдеры", 89, 12, sort_order=6),
    SeedCase(
        CaseCategory.THEMATIC, "thematic_anniversary", "Юбилейный", None, None, sort_order=7,
        note="Цена/кол-во предметов обрезаны на скриншоте.",
    ),
    SeedCase(
        CaseCategory.THEMATIC, "thematic_honey", "Медовый", None, None, sort_order=8,
        note="Цена/кол-во предметов обрезаны на скриншоте.",
    ),
    SeedCase(CaseCategory.THEMATIC, "thematic_six_seven", "Сикс Севен", 67, 10, sort_order=9),
    SeedCase(CaseCategory.THEMATIC, "thematic_hirsy", "Гирсы", 17, 14, sort_order=10),
    SeedCase(CaseCategory.THEMATIC, "thematic_losy", "Лосы", 139, 14, sort_order=11),
    SeedCase(CaseCategory.THEMATIC, "thematic_dlc", "ДЛС", 229, 9, sort_order=12),
    SeedCase(CaseCategory.THEMATIC, "thematic_basic", "Базовый", 9, 9, sort_order=13),
    SeedCase(CaseCategory.THEMATIC, "thematic_og", "ОГ", 10000, 10, sort_order=14),
    SeedCase(CaseCategory.THEMATIC, "thematic_garama", "Гарама", 39, 10, sort_order=15),
    SeedCase(CaseCategory.THEMATIC, "thematic_imperial", "Императорский", 34900, 11, sort_order=16),

    # --- ALL-IN ---
    SeedCase(CaseCategory.ALLIN, "allin_skibidi", "Скибиди Алл-ин", 29, 4, sort_order=1),
    SeedCase(CaseCategory.ALLIN, "allin_meowl", "Меовл Алл-ин", 39, 4, sort_order=2),
    SeedCase(CaseCategory.ALLIN, "allin_pork", "Порк Алл-ин", 39, 4, sort_order=3),
    SeedCase(CaseCategory.ALLIN, "allin_elephant", "Слон Алл-ин", 49, 4, sort_order=4),

    # --- ПАРТНЕРЫ ---
    SeedCase(CaseCategory.PARTNERS, "partners_nikil", "Никил", 49, 9, sort_order=1),
    SeedCase(
        CaseCategory.PARTNERS, "partners_lisharty", "Лишарти", None, 9, sort_order=2,
        note="Цена обрезана на скриншоте.",
    ),

    # --- БЕСПЛАТНЫЕ КЕЙСЫ --- (у большинства — особые условия открытия, не просто цена)
    SeedCase(
        CaseCategory.FREE, "free_daily", "Бесплатный", None, 11, sort_order=1,
        note="Открывается бесплатно раз в сутки по таймеру (на скриншоте «через 5ч 08м»).",
    ),
    SeedCase(
        CaseCategory.FREE, "free_deposit", "За депозит", None, 12, sort_order=2,
        note="Условие открытия — сумма депозитов (на скриншоте «Осталось 194 B» до цели).",
    ),
    SeedCase(
        CaseCategory.FREE, "free_referral", "Реферальный", None, 9, sort_order=3,
        note="Разовый кейс за реферальную активность (на скриншоте уже был отмечен как «Уже забрано»).",
    ),
    SeedCase(CaseCategory.FREE, "free_crystal", "Кристальный", 109, 8, sort_order=4, note="Цена в 🎫."),
    SeedCase(CaseCategory.FREE, "free_phantom", "Фантомный", 240, 9, sort_order=5, note="Цена в 🎫."),
    SeedCase(
        CaseCategory.FREE, "free_staking", "За стейкинг", None, 18, sort_order=6,
        note="Условие открытия — активный стейк от 500 B (раздел «Бонусы» ещё не реализован).",
    ),
]
