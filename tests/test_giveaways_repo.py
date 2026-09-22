"""Тесты слоя БД: розыгрыши и участие."""
from __future__ import annotations

from datetime import datetime, timedelta

from bot.database import engine as engine_module
from bot.database.models import GiveawayStatus
from bot.database.repo import giveaways as giveaways_repo
from bot.database.repo import users as users_repo
from bot.services.giveaway_service import resolve_if_expired


async def test_create_and_join_giveaway():
    async with engine_module.async_session() as session:
        user = await users_repo.get_or_create_user(session, tg_id=1, username="a", first_name="A")
        giveaway = await giveaways_repo.create(
            session, "Test", "Prize", datetime.utcnow() + timedelta(days=1), created_by_tg_id=999
        )

        assert await giveaways_repo.get_entry(session, giveaway, user) is None
        await giveaways_repo.join(session, giveaway, user)
        assert await giveaways_repo.get_entry(session, giveaway, user) is not None
        assert await giveaways_repo.count_entries(session, giveaway) == 1


async def test_resolve_if_expired_picks_winner_from_entrants():
    async with engine_module.async_session() as session:
        user1 = await users_repo.get_or_create_user(session, tg_id=1, username="a", first_name="A")
        user2 = await users_repo.get_or_create_user(session, tg_id=2, username="b", first_name="B")
        giveaway = await giveaways_repo.create(
            session, "Test", "Prize", datetime.utcnow() - timedelta(seconds=1), created_by_tg_id=999
        )
        await giveaways_repo.join(session, giveaway, user1)
        await giveaways_repo.join(session, giveaway, user2)

        resolved = await resolve_if_expired(session, giveaway)
        assert resolved.status == GiveawayStatus.RESOLVED
        assert resolved.winner_user_id in (user1.id, user2.id)


async def test_resolve_if_expired_no_entrants_gives_no_winner():
    async with engine_module.async_session() as session:
        giveaway = await giveaways_repo.create(
            session, "Empty", "Prize", datetime.utcnow() - timedelta(seconds=1), created_by_tg_id=999
        )
        resolved = await resolve_if_expired(session, giveaway)
        assert resolved.status == GiveawayStatus.RESOLVED
        assert resolved.winner_user_id is None


async def test_resolve_if_expired_noop_when_not_expired():
    async with engine_module.async_session() as session:
        giveaway = await giveaways_repo.create(
            session, "Future", "Prize", datetime.utcnow() + timedelta(days=1), created_by_tg_id=999
        )
        resolved = await resolve_if_expired(session, giveaway)
        assert resolved.status == GiveawayStatus.ACTIVE
