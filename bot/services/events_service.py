"""Глобальные ивенты: админ одной кнопкой включает на N часов для всех.

  * luck     — «Удача ×N»: шанс окупающего дропа в кейсах и батле и шанс
               апгрейдера умножаются на N (поверх личной подкрутки; личная
               ×0 остаётся ×0);
  * discount — «Скидка −X%» на открытие кейсов и батлы;
  * deposit  — «Бонус +X%» к пополнениям брейнротами, гирсами и Stars;
  * sell     — «Продажа +X%»: брейнроты продаются дороже;
  * cashback — «Кэшбэк X%»: если открытие кейса не окупилось, X% от
               разницы (цена − дроп) возвращается на баланс;
  * battle   — «Батл-бонус +X%»: к победе в батле сверху X% от банка;
  * free     — «Бесплатный кейс каждые N минут» вместо обычного кулдауна;
  * upgrade  — «Апгрейд-буст +X%»: к шансу апгрейдера прибавляется X (до 95%);
  * double   — «Двойной дроп»: с шансом X% кейс даёт ещё один брейнрот;
  * quest    — «Квесты ×N»: награды за квесты умножаются.

Длительность задаётся в минутах.

Хранится в app_meta (event_<тип> = "значение|конец_unix"), копия — в
памяти: цены и шансы считаются синхронно в куче мест. Истёкший ивент
просто перестаёт действовать.
"""
from __future__ import annotations

import math
import json
import time
from contextvars import ContextVar
from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import AppMeta, PartnerCode, User
from bot.services import settings_service


@dataclass(frozen=True)
class EventType:
    code: str
    title: str
    emoji: str
    unit: str  # "x" | "%" | "min"
    min_value: float
    max_value: float
    default: float


TYPES: dict[str, EventType] = {
    "luck": EventType("luck", "Удача", "🍀", "x", 1.1, 5, 2),
    "discount": EventType("discount", "Скидка на кейсы", "🏷", "%", 5, 70, 20),
    "deposit": EventType("deposit", "Бонус к пополнению", "💎", "%", 5, 200, 25),
    "sell": EventType("sell", "Продажа дороже", "💰", "%", 5, 100, 20),
    "cashback": EventType("cashback", "Кэшбэк с кейсов", "🛟", "%", 5, 50, 15),
    "battle": EventType("battle", "Батл-бонус", "⚔️", "%", 10, 200, 50),
    "free": EventType("free", "Бесплатный кейс чаще", "⏱", "min", 5, 720, 60),
    "upgrade": EventType("upgrade", "Апгрейд-буст", "⬆️", "%", 2, 30, 10),
    "double": EventType("double", "Двойной дроп", "✌️", "%", 5, 50, 15),
    "quest": EventType("quest", "Квесты ×N", "📋", "x", 1.5, 5, 2),
    "contract": EventType("contract", "Контракт-буст", "📜", "%", 5, 50, 15),
}
MAX_MINUTES = 60 * 24 * 7

_active: dict[str, tuple[float, float]] = {}  # код → (значение, конец unix)
_started: dict[str, float] = {}  # код → старт unix (для полоски оставшегося времени)
_by: dict[str, str] = {}  # код → кто запустил («@admin», «🎲 автоивент»)
LOG_KEY = "event_log"  # журнал запусков/остановок для админки (JSON, последние LOG_LIMIT)
LOG_LIMIT = 50

# Партнёрские ивенты: id партнёрского кода → тип → (значение, конец, старт)
_partner: dict[int, dict[str, tuple[float, float, float]]] = {}
_audience: ContextVar[int | None] = ContextVar("event_audience", default=None)

# Потолки для партнёров: для «free» — минимальный интервал, для остальных — максимум силы.
PARTNER_LIMITS: dict[str, float] = {
    "luck": 2, "discount": 30, "deposit": 50, "sell": 30, "cashback": 25, "battle": 100, "free": 30,
    "upgrade": 10, "double": 15, "quest": 2, "contract": 20,
}
PARTNER_MAX_MINUTES = 180
PARTNER_COOLDOWN_HOURS = 12


def _key(code: str) -> str:
    return f"event_{code}"


def active() -> dict[str, tuple[float, float]]:
    now = time.time()
    return {code: ev for code, ev in _active.items() if ev[1] > now}


def partner_active(pc_id: int | None) -> dict[str, tuple[float, float]]:
    now = time.time()
    return {code: (v, ends) for code, (v, ends, _) in _partner.get(pc_id or -1, {}).items() if ends > now}


def value(code: str) -> float | None:
    """Сила ивента для текущего игрока: глобальный и/или партнёрский (сильнейший)."""
    g = active().get(code)
    p = partner_active(_audience.get()).get(code)
    vals = [ev[0] for ev in (g, p) if ev]
    if not vals:
        return None
    return min(vals) if code == "free" else max(vals)  # у «free» сильнее — меньший интервал


def _event_json(code: str, v: float, ends: float, partner: bool, started: float | None = None) -> dict:
    duration = int(ends - started) if started and ends > started else None
    return {"type": code, "title": TYPES[code].title, "emoji": TYPES[code].emoji, "unit": TYPES[code].unit,
            "value": v, "ends_at": int(ends), "seconds_left": max(0, int(ends - time.time())), "partner": partner,
            "duration": duration}


def _partner_started(pc_id: int | None, code: str) -> float | None:
    ev = _partner.get(pc_id or -1, {}).get(code)
    return ev[2] if ev else None


def as_json() -> list[dict]:
    """Ивенты, которые действуют на текущего игрока (глобальные + его партнёра)."""
    pc = _audience.get()
    out = [_event_json(code, v, ends, False, _started.get(code)) for code, (v, ends) in sorted(active().items())]
    out += [_event_json(code, v, ends, True, _partner_started(pc, code))
            for code, (v, ends) in sorted(partner_active(pc).items())]
    return out


def set_audience(pc_id: int | None):
    return _audience.set(pc_id)


def reset_audience(token) -> None:
    _audience.reset(token)


async def audience_of(session: AsyncSession, user: User | None) -> int | None:
    """Партнёр игрока: активированный партнёрский код или реферер-партнёр."""
    if user is None:
        return None
    if user.partner_code_id:
        return user.partner_code_id
    if user.referred_by_id:
        return (await session.execute(
            select(PartnerCode.id).where(PartnerCode.user_id == user.referred_by_id, PartnerCode.is_active.is_(True))
        )).scalar_one_or_none()
    return None


async def partner_audience_ids(session: AsyncSession, pc: PartnerCode) -> list[int]:
    """tg_id аудитории партнёра — для рассылки."""
    rows = await session.execute(
        select(User.tg_id).where(or_(User.partner_code_id == pc.id, User.referred_by_id == pc.user_id))
    )
    return list(rows.scalars().all())


async def load(session: AsyncSession) -> None:
    rows = (await session.execute(select(AppMeta).where(AppMeta.key.in_([_key(c) for c in TYPES])))).scalars().all()
    _active.clear()
    for row in rows:
        try:
            parts = row.value.split("|")
            code = row.key.removeprefix("event_")
            _active[code] = (float(parts[0]), float(parts[1]))
            if len(parts) > 2:
                _started[code] = float(parts[2])
            if len(parts) > 3:
                _by[code] = parts[3]
        except (ValueError, IndexError):
            continue
    _partner.clear()
    for row in (await session.execute(select(AppMeta).where(AppMeta.key.like("pevent_%")))).scalars().all():
        try:
            _, pc_id, code = row.key.split("_", 2)
            v, ends, started = row.value.split("|")
            if code in TYPES:
                _partner.setdefault(int(pc_id), {})[code] = (float(v), float(ends), float(started))
        except ValueError:
            continue


def _pkey(pc_id: int, code: str) -> str:
    return f"pevent_{pc_id}_{code}"


def partner_cooldown_left(pc_id: int, code: str) -> int:
    """Сколько секунд партнёру ждать до следующего запуска этого ивента."""
    ev = _partner.get(pc_id, {}).get(code)
    if not ev:
        return 0
    return max(0, int(ev[2] + PARTNER_COOLDOWN_HOURS * 3600 - time.time()))


def partner_types_json(pc_id: int) -> list[dict]:
    out = []
    for t in TYPES.values():
        cap = PARTNER_LIMITS[t.code]
        lo, hi = (cap, t.max_value) if t.code == "free" else (t.min_value, cap)
        out.append({"type": t.code, "title": t.title, "emoji": t.emoji, "unit": t.unit, "min": lo, "max": hi,
                    "default": min(max(t.default, lo), hi), "max_minutes": PARTNER_MAX_MINUTES,
                    "cooldown_left": partner_cooldown_left(pc_id, t.code)})
    return out


async def start_partner(session: AsyncSession, pc_id: int, code: str, val: float, minutes: float) -> None:
    t = TYPES[code]
    cap = PARTNER_LIMITS[code]
    lo, hi = (cap, t.max_value) if code == "free" else (t.min_value, cap)
    if not lo <= val <= hi:
        raise ValueError(f"{t.title}: для партнёров от {lo:g} до {hi:g}{UNIT_LABEL[t.unit]}")
    if not 1 <= minutes <= PARTNER_MAX_MINUTES:
        raise ValueError(f"Длительность: от 1 до {PARTNER_MAX_MINUTES} минут")
    if code in partner_active(pc_id):
        raise ValueError("Этот ивент уже идёт")
    left = partner_cooldown_left(pc_id, code)
    if left:
        raise ValueError(f"Снова можно через {left // 3600} ч {left % 3600 // 60} мин")
    now = time.time()
    ends = now + minutes * 60
    await settings_service.set_setting(session, _pkey(pc_id, code), f"{val:g}|{ends:.0f}|{now:.0f}")
    _partner.setdefault(pc_id, {})[code] = (val, ends, now)


async def stop_partner(session: AsyncSession, pc_id: int, code: str) -> None:
    """Досрочная остановка: ивент кончается, но кулдаун считается от старта."""
    ev = _partner.get(pc_id, {}).get(code)
    if not ev:
        return
    now = time.time()
    await settings_service.set_setting(session, _pkey(pc_id, code), f"{ev[0]:g}|{now:.0f}|{ev[2]:.0f}")
    _partner[pc_id][code] = (ev[0], now, ev[2])


def all_partner_events() -> list[tuple[int, dict]]:
    """Все идущие партнёрские ивенты — для админки."""
    return [(pc_id, _event_json(code, v, ends, True, _partner_started(pc_id, code)))
            for pc_id in _partner for code, (v, ends) in sorted(partner_active(pc_id).items())]


UNIT_LABEL = {"x": "×", "%": "%", "min": " мин"}


def started_by(code: str) -> str | None:
    return _by.get(code)


async def get_log(session: AsyncSession) -> list[dict]:
    raw = await settings_service.get_setting(session, LOG_KEY)
    try:
        return json.loads(raw) if raw else []
    except ValueError:
        return []


async def log(session: AsyncSession, action: str, code: str, by: str, val: float | None = None,
              minutes: float | None = None, scope: str | None = None) -> None:
    """Запись в журнал: action start|stop, scope — «для всех» или партнёрский код."""
    entries = await get_log(session)
    entries.insert(0, {"action": action, "type": code, "value": val, "minutes": minutes, "by": by,
                       "scope": scope, "at": int(time.time())})
    await settings_service.set_setting(session, LOG_KEY, json.dumps(entries[:LOG_LIMIT], ensure_ascii=False))


async def start(session: AsyncSession, code: str, val: float, minutes: float, by: str = "") -> None:
    t = TYPES[code]
    if not t.min_value <= val <= t.max_value:
        raise ValueError(f"{t.title}: от {t.min_value:g} до {t.max_value:g}{UNIT_LABEL[t.unit]}")
    if not 1 <= minutes <= MAX_MINUTES:
        raise ValueError(f"Длительность: от 1 до {MAX_MINUTES} минут")
    now = time.time()
    ends = now + minutes * 60
    by = by.replace("|", "/")
    await settings_service.set_setting(session, _key(code), f"{val:g}|{ends:.0f}|{now:.0f}|{by}")
    _active[code] = (val, ends)
    _started[code] = now
    _by[code] = by
    await log(session, "start", code, by, val, minutes)


async def stop(session: AsyncSession, code: str, by: str = "") -> None:
    was_on = code in active()
    await settings_service.set_setting(session, _key(code), None)
    _active.pop(code, None)
    _by.pop(code, None)
    if was_on:
        await log(session, "stop", code, by)


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


def sell_payout(item_value: int) -> int:
    """Сколько B дают за продажу брейнрота (с ивентом «Продажа дороже»)."""
    return round(item_value * (1 + (value("sell") or 0) / 100))


def cashback(cost: int, dropped_value: int) -> int:
    """Кэшбэк за неокупившееся открытие (0 — нет ивента или окупилось)."""
    pct = value("cashback")
    if not pct or cost <= 0 or dropped_value >= cost:
        return 0
    return int((cost - dropped_value) * pct / 100)


def battle_bonus(pot: int) -> int:
    pct = value("battle")
    return int(pot * pct / 100) if pct else 0


def upgrade_bonus() -> float:
    return value("upgrade") or 0.0


def upgrade_chances(chance: float, personal_luck: float | None) -> tuple[float, float]:
    """(шанс, который видит игрок; реальный шанс) апгрейдера с ивентами.
    Апгрейд-буст виден игроку (+X к шансу), подкрутка — нет; личная ×0 —
    никогда не заходит."""
    bonus = upgrade_bonus()
    shown = min(95, chance + bonus)
    luck = effective_luck(personal_luck)
    if luck == 0:
        return shown, 0
    real = chance if luck is None else min(95, chance * luck)
    return shown, min(95, real + bonus)


def contract_bonus() -> float:
    """Ивент «Контракт-буст»: +X% к множителю контракта."""
    return value("contract") or 0.0


def double_drop_chance() -> float:
    return (value("double") or 0.0) / 100


def quest_multiplier() -> float:
    return value("quest") or 1.0


def free_cooldown_hours(base_hours: float) -> float:
    minutes = value("free")
    return min(base_hours, minutes / 60) if minutes else base_hours


def duration_label(minutes: float) -> str:
    minutes = round(minutes)
    h, m = divmod(minutes, 60)
    if not h:
        return f"{m} мин"
    return f"{h} ч {m} мин" if m else f"{h} ч"


def announcement(code: str, val: float, minutes: float) -> str:
    """Текст рассылки о запуске ивента."""
    t = TYPES[code]
    left = duration_label(minutes)
    what = {
        "luck": f"<b>Удача ×{val:g}</b> — у всех выше шанс окупающего дропа в кейсах и батлах и шанс апгрейда.",
        "discount": f"<b>Скидка −{val:g}%</b> на все платные кейсы и батлы.",
        "deposit": f"<b>+{val:g}% к пополнению</b> брейнротами, гирсами и Stars.",
        "sell": f"<b>Продажа +{val:g}%</b> — брейнроты продаются дороже.",
        "cashback": f"<b>Кэшбэк {val:g}%</b> — если кейс не окупился, часть потерянного вернётся на баланс.",
        "battle": f"<b>Батл-бонус +{val:g}%</b> — к каждой победе в батле сверху.",
        "free": f"<b>Бесплатный кейс каждые {val:g} мин</b> вместо обычного ожидания.",
        "upgrade": f"<b>Апгрейд-буст +{val:g}%</b> — к каждому шансу в апгрейдере.",
        "double": f"<b>Двойной дроп</b> — с шансом {val:g}% кейс даёт второй брейнрот бесплатно.",
        "quest": f"<b>Квесты ×{val:g}</b> — награды за все квесты умножаются.",
        "contract": f"<b>Контракт-буст +{val:g}%</b> — каждый контракт даёт брейнрота дороже.",
    }[code]
    return f"{t.emoji} <b>ИВЕНТ В BRAINCORE!</b>\n\n{what}\n\n⏳ Действует {left} — успей!"
