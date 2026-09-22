"""Логика краша: рост множителя и точка обрыва.

[ЛОГИЧЕСКИ ПРЕДПОЛОЖЕНО] На скриншоте виден только растущий множитель
(«2.78x», подпись «В ПОЛЁТЕ») и лента истории раундов («1.00x, 1.40x,
2.00x…») — ни формула роста, ни распределение точки краша нигде не
подписаны числом. Ниже — стандартная для «crash»-игр модель: множитель
растёт по экспоненте от времени, точка обрыва — из хвостатого распределения
1/U с хаус-эджем, обе части вынесены в конфиг и легко заменить.

В отличие от оригинала (общий раунд на всех игроков с живой анимацией в
Mini App), раунд здесь личный для каждого игрока: Telegram-бот не может
синхронизированно транслировать один и тот же полёт ракеты всем участникам
одновременно — у каждого игрока свой независимый раунд.
"""
from __future__ import annotations

import random

from bot.config import config


def multiplier_at(elapsed_seconds: float) -> float:
    ticks = elapsed_seconds / config.crash_tick_seconds
    raw = (1 + config.crash_growth_rate) ** ticks
    return round(min(raw, config.crash_max_multiplier), 2)


def generate_crash_point() -> float:
    r = random.random()
    if r <= 1e-9:
        r = 1e-9
    raw = config.crash_house_edge / r
    return max(1.00, round(min(raw, config.crash_max_multiplier), 2))
