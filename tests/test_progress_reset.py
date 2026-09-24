"""Разовый откат прогресса при переходе с демо-режима на настоящий баланс."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import bot.database.engine as engine_module
from bot.database.models import (
    AppMeta,
    Base,
    CaseCredit,
    InventoryItem,
    PartnerCode,
    PromoCode,
    PromoKind,
    PromoRedemption,
    User,
)


async def _count(session, model) -> int:
    return (await session.execute(select(func.count()).select_from(model))).scalar_one()


async def test_reset_wipes_progress_keeps_accounts_and_backs_up(tmp_path, monkeypatch) -> None:
    db = tmp_path / "bot.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db}")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(engine_module, "engine", engine)
    monkeypatch.setattr(engine_module, "async_session", sessions)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with sessions() as session:
        user = User(tg_id=1, referral_code="R1", balance=500, game_tokens=9000, referral_earned_total=40)
        session.add(user)
        await session.flush()
        promo = PromoCode(code="P", kind=PromoKind.BALANCE, amount=10, uses=3, created_by_tg_id=1)
        session.add_all([
            InventoryItem(user_id=user.id, case_name="x", item_name="67", value=5),
            CaseCredit(user_id=user.id, case_code="tirili", count=2),
            PartnerCode(code="MEGA", user_id=user.id),
            promo,
        ])
        await session.flush()
        session.add(PromoRedemption(promo_id=promo.id, user_id=user.id))
        await session.commit()

    await engine_module._reset_progress_once()

    async with sessions() as session:
        user = (await session.execute(select(User))).scalar_one()
        assert (user.balance, user.game_tokens, user.referral_earned_total) == (0, 0, 0)
        for model in (InventoryItem, CaseCredit, PromoRedemption):
            assert await _count(session, model) == 0
        assert await _count(session, PartnerCode) == 1  # партнёрки остаются
        assert (await session.execute(select(PromoCode.uses))).scalar_one() == 0
        marker = await session.get(AppMeta, engine_module.PROGRESS_RESET_KEY)
        assert marker.value == engine_module.PROGRESS_RESET_ID

    assert list(tmp_path.glob("bot-before-reset-*.db")), "перед откатом должна появиться копия БД"

    # повторный старт ничего не трогает
    async with sessions() as session:
        (await session.execute(select(User))).scalar_one().balance = 77
        await session.commit()
    await engine_module._reset_progress_once()
    async with sessions() as session:
        assert (await session.execute(select(User))).scalar_one().balance == 77
    await engine.dispose()
