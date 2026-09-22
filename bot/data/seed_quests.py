"""Сид-данные квестов.

[ПОДТВЕРЖДЕНО СКРИНШОТОМ] «Открой Сикс Севен» и «Сыграй в апгрейдере» — с
точными текстами, целями (0/1) и наградами (+23 🎫 / +6 🎫). Недельный
«Открой Тако 3 раза» виден только заголовком снизу экрана (обрезан) —
reward_tokens для него [ЛОГИЧЕСКИ ПРЕДПОЛОЖЕНО].
"""
from __future__ import annotations

from dataclasses import dataclass

from bot.database.models import QuestScope


@dataclass(frozen=True)
class SeedQuest:
    code: str
    scope: QuestScope
    title: str
    description: str
    target_type: str
    target_count: int
    reward_tokens: int
    sort_order: int


SEED_QUESTS: list[SeedQuest] = [
    SeedQuest(
        code="daily_open_six_seven",
        scope=QuestScope.DAILY,
        title="Открой Сикс Севен",
        description="Открой кейс «Сикс Севен» один раз.",
        target_type="open_case:cases_six_seven",
        target_count=1,
        reward_tokens=23,
        sort_order=1,
    ),
    SeedQuest(
        code="daily_upgrader_spin",
        scope=QuestScope.DAILY,
        title="Сыграй в апгрейдере",
        description="Сделай один спин в апгрейдере.",
        target_type="upgrader_spin",
        target_count=1,
        reward_tokens=6,
        sort_order=2,
    ),
    SeedQuest(
        code="weekly_open_tako_3",
        scope=QuestScope.WEEKLY,
        title="Открой Тако 3 раза",
        description="Открой кейс «Тако» три раза.",
        target_type="open_case:cases_tako",
        target_count=3,
        reward_tokens=60,
        sort_order=1,
    ),
]
