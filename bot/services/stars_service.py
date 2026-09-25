"""Пополнение Telegram Stars: курс и бонус за код.

Курс — STARS_RATE B за 1 ⭐ (по умолчанию 1.75, меняется в админке).
Бонус +N% (по умолчанию 10, тоже в админке) даёт любой рабочий код:
промокод, партнёрский код или реферальный код другого игрока. Код только
проверяется — промокод от этого не тратится. Если у партнёрского кода свой
бонус к пополнению выше — берётся он. Сумма к зачислению фиксируется при
создании счёта (StarsDeposit.credited_b), зачисление — по successful_payment.
"""
from __future__ import annotations

import math
import secrets
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import PartnerCode, PromoCode, StarsDeposit, User
from bot.services import events_service, settings_service

STARS_RATE = "stars_rate"
STARS_CODE_BONUS = "stars_code_bonus_percent"
DEFAULT_STARS_RATE = 1.75
DEFAULT_STARS_CODE_BONUS = 10.0


class BadCode(Exception):
    pass


@dataclass
class StarsQuote:
    stars: int
    rate: float
    bonus_percent: float
    code: str | None
    credited: int


async def _float_setting(session: AsyncSession, key: str, default: float) -> float:
    raw = await settings_service.get_setting(session, key)
    try:
        return float(raw) if raw else default
    except ValueError:
        return default


async def rate(session: AsyncSession) -> float:
    return await _float_setting(session, STARS_RATE, DEFAULT_STARS_RATE)


async def code_bonus(session: AsyncSession) -> float:
    return await _float_setting(session, STARS_CODE_BONUS, DEFAULT_STARS_CODE_BONUS)


async def code_bonus_percent(session: AsyncSession, user: User, raw_code: str | None) -> tuple[str | None, float]:
    """(нормализованный код, бонус %) или BadCode. Пустой код — без бонуса."""
    code = (raw_code or "").strip().upper()
    if not code:
        return None, 0.0
    bonus = await code_bonus(session)
    promo = (await session.execute(select(PromoCode).where(func.upper(PromoCode.code) == code))).scalar_one_or_none()
    if promo is not None:
        return code, bonus
    partner = (await session.execute(
        select(PartnerCode).where(func.upper(PartnerCode.code) == code, PartnerCode.is_active.is_(True))
    )).scalar_one_or_none()
    if partner is not None and partner.user_id != user.id:
        return code, max(bonus, partner.deposit_bonus_percent or 0)
    referrer = (await session.execute(select(User).where(func.upper(User.referral_code) == code))).scalar_one_or_none()
    if referrer is not None and referrer.id != user.id:
        return code, bonus
    raise BadCode


async def quote(session: AsyncSession, user: User, stars: int, raw_code: str | None) -> StarsQuote:
    code, bonus = await code_bonus_percent(session, user, raw_code)
    bonus += events_service.deposit_bonus_percent()  # ивент «Бонус к пополнению»
    r = await rate(session)
    credited = math.floor(stars * r * (1 + bonus / 100))
    return StarsQuote(stars=stars, rate=r, bonus_percent=bonus, code=code, credited=credited)


async def create_deposit(session: AsyncSession, user: User, q: StarsQuote) -> StarsDeposit:
    deposit = StarsDeposit(
        user_id=user.id, stars_amount=q.stars, promo_code=q.code, credited_b=q.credited,
        payload=f"stars_dep:{user.tg_id}:{secrets.token_hex(6)}", status="pending",
    )
    session.add(deposit)
    await session.commit()
    return deposit
