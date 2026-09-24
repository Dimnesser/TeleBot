"""Сид-данные квестов.

Форма квестов (дневной «открой кейс», дневной «спин в апгрейдере»,
недельный «открой кейс ×3») — со скриншота. Квесты на кейсы указывают на
кейсы из bot/data/seed_cases.py; при пересеве каталога старые квесты
переписываются на эти (bot.database.engine._retarget_stale_case_quests).
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
        code="daily_open_fastfood",
        scope=QuestScope.DAILY,
        title="Перекус",
        description="Открой кейс «Фастфуд» один раз.",
        target_type="open_case:fastfood",
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
        code="weekly_open_dragon_3",
        scope=QuestScope.WEEKLY,
        title="Укротитель драконов",
        description="Открой кейс «Драгон» три раза.",
        target_type="open_case:dragon",
        target_count=3,
        reward_tokens=240,
        sort_order=1,
    ),
]
