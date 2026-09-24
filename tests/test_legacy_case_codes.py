"""Пересев каталога переносит выданные открытия, промокоды и партнёрские
коды со старых кодов кейсов на новые — ничего не «виснет»."""
from __future__ import annotations

from sqlalchemy import select

import bot.database.engine as engine_module
from bot.database.models import CaseCredit, PartnerCode, PromoCode, PromoKind, User


async def test_reseed_remaps_legacy_case_codes(in_memory_db) -> None:
    async with in_memory_db() as session:
        user = User(tg_id=1, referral_code="r1")
        session.add(user)
        await session.flush()
        session.add_all([
            CaseCredit(user_id=user.id, case_code="referral_gift", count=2),
            CaseCredit(user_id=user.id, case_code="nonna_kitchen", count=1),
            CaseCredit(user_id=user.id, case_code="fastfood", count=3),
            PartnerCode(code="MEGA", user_id=user.id, case_code="referral_gift", case_amount=2),
            PromoCode(code="OLD", kind=PromoKind.CASE, amount=1, case_code="abyss_dive", created_by_tg_id=1),
        ])
        await session.commit()

    await engine_module._seed_cases_reconcile()

    async with in_memory_db() as session:
        credits = {c.case_code: c.count for c in (await session.execute(select(CaseCredit))).scalars()}
        assert credits == {"referral": 2, "fastfood": 4}
        assert (await session.execute(select(PartnerCode.case_code))).scalar_one() == "referral"
        assert (await session.execute(select(PromoCode.case_code))).scalar_one() == "capitano"
