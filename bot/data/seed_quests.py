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
        code="daily_open_nonna_kitchen",
        scope=QuestScope.DAILY,
        title="Загляни на Кухню Нонны",
        description="Открой кейс «Кухня Нонны» один раз.",
        target_type="open_case:nonna_kitchen",
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
        code="weekly_open_dragon_forge_3",
        scope=QuestScope.WEEKLY,
        title="Три удара молота",
        description="Открой кейс «Драконья Кузня» три раза.",
        target_type="open_case:dragon_forge",
        target_count=3,
        reward_tokens=240,
        sort_order=1,
    ),
]
