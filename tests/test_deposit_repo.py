"""Тесты слоя БД: пользователи, каталог, заявки на депозит и очередь."""
from __future__ import annotations

from bot.database import engine as engine_module
from bot.database.models import DepositCategory, DepositItem, DepositRequestStatus
from bot.database.repo import deposit_items as items_repo
from bot.database.repo import deposit_requests as requests_repo
from bot.database.repo import users as users_repo


async def _seed_one_item(session, category=DepositCategory.BRAINROT, price=100, min_qty=1) -> DepositItem:
    item = DepositItem(category=category, name="Test Item", emoji="🧩", price_b=price, min_qty=min_qty)
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


async def test_get_or_create_user_is_idempotent():
    async with engine_module.async_session() as session:
        first = await users_repo.get_or_create_user(session, tg_id=1, username="a", first_name="A")
        second = await users_repo.get_or_create_user(session, tg_id=1, username="a", first_name="A")
        assert first.id == second.id
        assert first.balance == 0
        assert first.referral_code


async def test_referral_code_links_referred_user():
    async with engine_module.async_session() as session:
        referrer = await users_repo.get_or_create_user(session, tg_id=1, username="ref", first_name="R")
        referred = await users_repo.get_or_create_user(
            session, tg_id=2, username="new", first_name="N", referral_code=referrer.referral_code
        )
        assert referred.referred_by_id == referrer.id


async def test_list_items_filters_by_category_search_and_sort():
    async with engine_module.async_session() as session:
        session.add_all(
            [
                DepositItem(category=DepositCategory.BRAINROT, name="Kraken", emoji="🐙", price_b=3000, min_qty=1),
                DepositItem(category=DepositCategory.BRAINROT, name="Cash or Card", emoji="💳", price_b=40, min_qty=2),
                DepositItem(category=DepositCategory.HIRSY, name="Witch Broom", emoji="🧹", price_b=38, min_qty=2),
            ]
        )
        await session.commit()

        brainrots = await items_repo.list_items(session, DepositCategory.BRAINROT)
        assert {item.name for item in brainrots} == {"Kraken", "Cash or Card"}

        found = await items_repo.list_items(session, DepositCategory.BRAINROT, search="kra")
        assert [item.name for item in found] == ["Kraken"]

        by_price_desc = await items_repo.list_items(session, DepositCategory.BRAINROT, sort_desc=True)
        assert [item.name for item in by_price_desc] == ["Kraken", "Cash or Card"]


async def test_deposit_request_lifecycle_approve_credits_balance():
    async with engine_module.async_session() as session:
        user = await users_repo.get_or_create_user(session, tg_id=10, username="u", first_name="U")
        item = await _seed_one_item(session)

        request = await requests_repo.create_request(
            session,
            user,
            DepositCategory.BRAINROT,
            {item.id: 1},
            buff="none",
            game_nickname="Nick",
            total_b=100,
        )
        assert request.status == DepositRequestStatus.PENDING

        fetched = await requests_repo.get_request(session, request.id)
        assert fetched is not None
        assert fetched.items == {str(item.id): 1}

        await requests_repo.resolve_request(session, fetched, DepositRequestStatus.APPROVED, admin_id=999)
        assert fetched.status == DepositRequestStatus.APPROVED
        assert fetched.admin_id == 999
        assert fetched.resolved_at is not None


async def test_queue_promotion_picks_oldest_queued_request():
    async with engine_module.async_session() as session:
        user = await users_repo.get_or_create_user(session, tg_id=20, username="u2", first_name="U2")
        item = await _seed_one_item(session)

        first = await requests_repo.create_request(
            session, user, DepositCategory.BRAINROT, {item.id: 1}, buff="none",
            game_nickname="First", total_b=100, status=DepositRequestStatus.QUEUED,
        )
        second = await requests_repo.create_request(
            session, user, DepositCategory.BRAINROT, {item.id: 1}, buff="none",
            game_nickname="Second", total_b=100, status=DepositRequestStatus.QUEUED,
        )

        assert await requests_repo.count_status(session, DepositRequestStatus.QUEUED) == 2

        oldest = await requests_repo.get_oldest_queued(session)
        assert oldest.id == first.id

        await requests_repo.promote_to_pending(session, oldest)
        assert oldest.status == DepositRequestStatus.PENDING

        remaining_queued = await requests_repo.get_oldest_queued(session)
        assert remaining_queued.id == second.id
