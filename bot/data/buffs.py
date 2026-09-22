"""Варианты «бафов» для депозита предметами.

[ЛОГИЧЕСКИ ПРЕДПОЛОЖЕНО] На скриншотах виден только заголовок «Бафы — доплата
автоматически» с набором эмодзи-иконок без подписанных процентов. Точные
названия и наценки бафов по скриншотам определить нельзя, поэтому здесь
задан плейсхолдер-список с понятной структурой (код, подпись, % наценки),
который легко заменить на реальные данные, когда они станут известны.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BuffOption:
    code: str
    label: str
    surcharge_percent: int


BUFF_OPTIONS: list[BuffOption] = [
    BuffOption(code="none", label="Без бафов", surcharge_percent=0),
    BuffOption(code="combo1", label="🦅🇧🇷 Комбо +5%", surcharge_percent=5),
    BuffOption(code="combo2", label="⭕💀 Комбо +10%", surcharge_percent=10),
    BuffOption(code="combo3", label="Ⓩ Особый +15%", surcharge_percent=15),
]
