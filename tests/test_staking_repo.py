"""Тесты слоя БД: позиции стейкинга."""
from __future__ import annotations

from bot.database import engine as engine_module
from bot.database.models import StakeStatus
from bot.database.repo import staking as staking_repo
from bot.database.repo import users as users_repo


async def test_create_position_sets_matures_at_from_term_days():
    async with engine_module.async_session() as session:
        user = await users_repo.get_or_create_user(session, tg_id=1, username="a", first_name="A")
        position = await staking_repo.create_position(session, user, amount=500, term_days=7, bonus_percent=10.0)

        assert position.status == StakeStatus.ACTIVE
        delta = position.matures_at - position.started_at
        assert delta.days == 7


async def test_get_active_position_only_returns_active():
    async with engine_module.async_session() as session:
        user = await users_repo.get_or_create_user(session, tg_id=2, username="b", first_name="B")
        assert await staking_repo.get_active_position(session, user) is None

        position = await staking_repo.create_position(session, user, amount=100, term_days=7, bonus_percent=10.0)
        active = await staking_repo.get_active_position(session, user)
        assert active is not None and active.id == position.id

        position.status = StakeStatus.COMPLETED
        await session.commit()
        assert await staking_repo.get_active_position(session, user) is None


async def test_list_completed_and_list_all():
    async with engine_module.async_session() as session:
        user = await users_repo.get_or_create_user(session, tg_id=3, username="c", first_name="C")
        p1 = await staking_repo.create_position(session, user, amount=100, term_days=7, bonus_percent=10.0)
        p1.status = StakeStatus.COMPLETED
        await session.commit()

        all_positions = await staking_repo.list_all_for_user(session, user)
        completed = await staking_repo.list_completed(session, user)
        assert len(all_positions) == 1
        assert len(completed) == 1
        assert completed[0].id == p1.id
