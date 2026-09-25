"""Логика апгрейдера: расчёт шанса, подбор цели по пресету, розыгрыш.

[ЛОГИЧЕСКИ ПРЕДПОЛОЖЕНО] Формула шанса нигде на скриншоте не подписана
числом — виден только индикатор «ШАНС» на круговом диске и кнопки-пресеты
«x2 / x5 / x10 / 30% / 50% / 75%». Стандартная для таких апгрейдеров формула
(и единственная, которая делает кнопки-множители и кнопки-проценты
взаимно согласованными) — chance = вклад / цель, обрезанный до разумных
границ, чтобы не было гарантированных 0%/100% исходов.
"""
from __future__ import annotations

import random

from bot.config import config
from bot.database.repo.known_items import KnownItem


# Отдача апгрейдера, %: шанс = вклад / цель × отдача. 100 — честно 1:1,
# 80 — x2 даёт 40%, шанс 75% — цель чуть дороже вклада. Меняется в админке, хранится в app_meta
# (settings_service.UPGRADER_RTP) и подгружается при старте.
DEFAULT_RTP_PERCENT = 80.0
RTP_PERCENT = DEFAULT_RTP_PERCENT


def set_rtp(percent: float) -> None:
    global RTP_PERCENT
    RTP_PERCENT = float(percent)


async def load_rtp(session) -> float:
    from bot.services import settings_service
    raw = await settings_service.get_setting(session, settings_service.UPGRADER_RTP)
    try:
        set_rtp(float(raw) if raw else DEFAULT_RTP_PERCENT)
    except ValueError:
        set_rtp(DEFAULT_RTP_PERCENT)
    return RTP_PERCENT


def chance_percent(contribution_value: int, target_value: int, rtp: float | None = None) -> int:
    if target_value <= 0:
        return config.upgrader_max_chance_percent
    raw = round(contribution_value / target_value * (RTP_PERCENT if rtp is None else rtp))
    return max(config.upgrader_min_chance_percent, min(config.upgrader_max_chance_percent, raw))


def target_value_for_multiplier(contribution_value: int, multiplier: int) -> int:
    return max(contribution_value * multiplier, contribution_value + 1)


def target_value_for_chance(contribution_value: int, chance: int) -> int:
    chance = max(1, min(chance, 100))
    return max(round(contribution_value * 100 / chance), contribution_value + 1)


def find_nearest_target(
    known_items: list[KnownItem], target_value: int, exclude_name: str | None = None
) -> KnownItem | None:
    """Ищет известный предмет, ближайший к target_value, дороже вклада."""
    candidates = [item for item in known_items if item.name != exclude_name]
    if not candidates:
        return None
    return min(candidates, key=lambda item: abs(item.value - target_value))


def roll_success(chance: int) -> bool:
    return random.uniform(0, 100) < chance


def lucky_chance(chance: float, luck: float | None) -> float:
    """Реальный шанс с подкруткой админа (User.luck): None — честный,
    0 — апгрейд никогда не зайдёт, иначе шанс × luck (не выше 95%)."""
    return chance if luck is None else min(95, chance * luck)
