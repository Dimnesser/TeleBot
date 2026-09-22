"""Тесты подсчёта рефералов и начисления комиссии."""
from __future__ import annotations

from bot.database import engine as engine_module
from bot.database.repo.users import count_referrals, get_or_create_user
from bot.services.referral_service import credit_referral_commission


async def test_count_referrals_counts_only_direct_referrals():
    async with engine_module.async_session() as session:
        referrer = await get_or_create_user(session, tg_id=1, username="ref", first_name="R")
        assert await count_referrals(session, referrer) == 0

        await get_or_create_user(session, tg_id=2, username="u2", first_name="U2", referral_code=referrer.referral_code)
        await get_or_create_user(session, tg_id=3, username="u3", first_name="U3", referral_code=referrer.referral_code)
        unrelated = await get_or_create_user(session, tg_id=4, username="u4", first_name="U4")

        assert await count_referrals(session, referrer) == 2
        assert await count_referrals(session, unrelated) == 0


async def test_credit_referral_commission_credits_bronze_tier():
    async with engine_module.async_session() as session:
        referrer = await get_or_create_user(session, tg_id=1, username="ref", first_name="R")
        referred = await get_or_create_user(
            session, tg_id=2, username="u2", first_name="U2", referral_code=referrer.referral_code
        )

        credited = await credit_referral_commission(session, referred, deposit_total_b=1000)
        assert credited == 30  # Бронза 3%

        await session.refresh(referrer)
        assert referrer.balance == 30
        assert referrer.referral_earned_total == 30


async def test_credit_referral_commission_noop_without_referrer():
    async with engine_module.async_session() as session:
        user = await get_or_create_user(session, tg_id=1, username="solo", first_name="S")
        credited = await credit_referral_commission(session, user, deposit_total_b=1000)
        assert credited == 0
