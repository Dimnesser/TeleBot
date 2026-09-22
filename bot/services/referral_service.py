"""Начисление реферальной комиссии с одобренных депозитов.

[ПОДТВЕРЖДЕНО СКРИНШОТОМ] «Приглашай друзей и получай процент с их
депозитов» + тир Бронза = 3% комиссии. Здесь комиссия считается с суммы
одобренного депозита (B) и зачисляется рефереру на реальный баланс —
единственная точка входа реальных B помимо самого обменника/Stars.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from bot.data.referral_tiers import tier_for_count
from bot.database.models import User
from bot.database.repo.users import count_referrals, get_user_by_id


async def credit_referral_commission(session: AsyncSession, referred_user: User, deposit_total_b: int) -> int:
    """Возвращает зачисленную сумму (0, если рефера нет)."""
    if referred_user.referred_by_id is None or deposit_total_b <= 0:
        return 0

    referrer = await get_user_by_id(session, referred_user.referred_by_id)
    if referrer is None:
        return 0

    referral_count = await count_referrals(session, referrer)
    tier = tier_for_count(referral_count)
    commission = round(deposit_total_b * tier.commission_percent / 100)
    if commission <= 0:
        return 0

    referrer.balance += commission
    referrer.referral_earned_total += commission
    await session.commit()
    return commission
