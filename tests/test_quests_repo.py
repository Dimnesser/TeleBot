"""Тесты слоя БД: квесты и прогресс пользователя."""
from __future__ import annotations

from bot.database import engine as engine_module
from bot.database.models import Quest, QuestScope
from bot.database.repo import quests as quests_repo
from bot.database.repo import users as users_repo
from bot.services.quest_service import period_key, record_progress


async def _seed_quest(session, code="test_quest", target_type="open_case:test", target_count=2) -> Quest:
    quest = Quest(
        code=code,
        scope=QuestScope.DAILY,
        title="Test Quest",
        description="desc",
        target_type=target_type,
        target_count=target_count,
        reward_tokens=10,
    )
    session.add(quest)
    await session.commit()
    await session.refresh(quest)
    return quest


async def test_get_or_create_progress_is_idempotent():
    async with engine_module.async_session() as session:
        user = await users_repo.get_or_create_user(session, tg_id=1, username="a", first_name="A")
        quest = await _seed_quest(session)
        key = period_key(quest.scope)

        first = await quests_repo.get_or_create_progress(session, user, quest, key)
        second = await quests_repo.get_or_create_progress(session, user, quest, key)
        assert first.id == second.id
        assert first.progress_count == 0


async def test_record_progress_increments_matching_quest_only():
    async with engine_module.async_session() as session:
        user = await users_repo.get_or_create_user(session, tg_id=2, username="b", first_name="B")
        quest = await _seed_quest(session, code="q_six_seven", target_type="open_case:six_seven", target_count=2)
        other_quest = await _seed_quest(session, code="q_other", target_type="open_case:other", target_count=1)

        await record_progress(session, user, "open_case:six_seven")

        key = period_key(quest.scope)
        progress = await quests_repo.get_progress(session, user, quest, key)
        assert progress.progress_count == 1

        other_progress = await quests_repo.get_progress(session, user, other_quest, key)
        assert other_progress is None


async def test_record_progress_stops_at_target_count():
    async with engine_module.async_session() as session:
        user = await users_repo.get_or_create_user(session, tg_id=3, username="c", first_name="C")
        quest = await _seed_quest(session, target_type="open_case:capped", target_count=2)

        for _ in range(5):
            await record_progress(session, user, "open_case:capped")

        key = period_key(quest.scope)
        progress = await quests_repo.get_progress(session, user, quest, key)
        assert progress.progress_count == 2


async def test_record_progress_ignores_claimed_quest():
    async with engine_module.async_session() as session:
        user = await users_repo.get_or_create_user(session, tg_id=4, username="d", first_name="D")
        quest = await _seed_quest(session, target_type="open_case:claimed", target_count=1)
        key = period_key(quest.scope)

        progress = await quests_repo.get_or_create_progress(session, user, quest, key)
        progress.claimed = True
        await session.commit()

        await record_progress(session, user, "open_case:claimed")

        refreshed = await quests_repo.get_progress(session, user, quest, key)
        assert refreshed.progress_count == 0
