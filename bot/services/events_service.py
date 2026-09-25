"""Глобальные ивенты: админ одной кнопкой включает на N часов для всех.

  * luck     — «Удача ×N»: шанс окупающего дропа в кейсах и батле и шанс
               апгрейдера умножаются на N (поверх личной подкрутки; личная
               ×0 остаётся ×0);
  * discount — «Скидка −X%» на открытие кейсов и батлы;
  * deposit  — «Бонус +X%» к пополнениям брейнротами, гирсами и Stars.

Хранится в app_meta (event_<тип> = "значение|конец_unix"), копия — в
памяти: цены и шансы считаются синхронно в куче мест. Истёкший ивент
просто перестаёт действовать.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import AppMeta
from bot.services import settings_service


@dataclass(frozen=True)
class EventType:
    code: str
    title: str
    emoji: str
    unit: str  # "x" | "%"
    min_value: float
    max_value: float
    default: float


TYPES: dict[str, EventType] = {
    "luck": EventType("luck", "Удача", "🍀", "x", 1.1, 5, 2),
    "discount": EventType("discount", "Скидка на кейсы", "🏷", "%", 5, 70, 20),
    "deposit": EventType("deposit", "Бонус к пополнению", "💎", "%", 5, 200, 25),
}
MAX_HOURS = 24 * 7

_active: dict[str, tuple[float, float]] = {}  # код → (значение, конец unix)


def _key(code: str) -> str:
    return f"event_{code}"


def active() -> dict[str, tuple[float, float]]:
    now = time.time()
    return {code: ev for code, ev in _active.items() if ev[1] > now}


def value(code: str) -> float | None:
    ev = active().get(code)
    return ev[0] if ev else None


def as_json() -> list[dict]:
    return [
        {"type": code, "title": TYPES[code].title, "emoji": TYPES[code].emoji, "unit": TYPES[code].unit,
         "value": v, "ends_at": int(ends), "seconds_left": max(0, int(ends - time.time()))}
        for code, (v, ends) in sorted(active().items())
    ]


async def load(session: AsyncSession) -> None:
    rows = (await session.execute(select(AppMeta).where(AppMeta.key.in_([_key(c) for c in TYPES])))).scalars().all()
    _active.clear()
    for row in rows:
        try:
            v, ends = row.value.split("|")
            _active[row.key.removeprefix("event_")] = (float(v), float(ends))
        except ValueError:
            continue


async def start(session: AsyncSession, code: str, val: float, hours: float) -> None:
    t = TYPES[code]
    if not t.min_value <= val <= t.max_value:
        raise ValueError(f"{t.title}: от {t.min_value:g} до {t.max_value:g}{'×' if t.unit == 'x' else '%'}")
    if not 0 < hours <= MAX_HOURS:
        raise ValueError(f"Длительность: до {MAX_HOURS} часов")
    ends = time.time() + hours * 3600
    await settings_service.set_setting(session, _key(code), f"{val:g}|{ends:.0f}")
    _active[code] = (val, ends)


async def stop(session: AsyncSession, code: str) -> None:
    await settings_service.set_setting(session, _key(code), None)
    _active.pop(code, None)


# ---------------------------------------------------------------- эффекты

def effective_luck(personal: float | None) -> float | None:
    """Подкрутка с учётом ивента удачи: личная × ивент (личная ×0 — ×0)."""
    boost = value("luck")
    if not boost:
        return personal
    if personal == 0:
        return 0
    return (personal if personal is not None else 1) * boost


def price(base: int | None) -> int | None:
    """Цена открытия с учётом скидки (бесплатные остаются бесплатными)."""
    off = value("discount")
    if base is None or not base or not off:
        return base
    return max(1, math.ceil(base * (1 - off / 100)))


def deposit_bonus_percent() -> float:
    return value("deposit") or 0.0


def announcement(code: str, val: float, hours: float) -> str:
    """Текст рассылки о запуске ивента."""
    t = TYPES[code]
    left = f"{hours:g} ч" if hours >= 1 else f"{round(hours * 60)} мин"
    what = {
        "luck": f"<b>Удача ×{val:g}</b> — у всех выше шанс окупающего дропа в кейсах и батлах и шанс апгрейда.",
        "discount": f"<b>Скидка −{val:g}%</b> на все платные кейсы и батлы.",
        "deposit": f"<b>+{val:g}% к пополнению</b> брейнротами, гирсами и Stars.",
    }[code]
    return f"{t.emoji} <b>ИВЕНТ В BRAINCORE!</b>\n\n{what}\n\n⏳ Действует {left} — успей!"
