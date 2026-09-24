"""Тесты слоя БД: каталог кейсов, пулы дропа, инвентарь, демо-токены."""
from __future__ import annotations

from bot.database import engine as engine_module
from bot.database.models import Case, CaseCategory, CaseItem
from bot.database.repo import cases as cases_repo
from bot.database.repo import inventory as inventory_repo
from bot.database.repo import users as users_repo


async def _seed_case_with_items(session, category=CaseCategory.STARTER) -> Case:
    case = Case(category=category, code="seed_case", name="Seed Case", price_tokens=50, item_count_label=2, is_openable=True)
    session.add(case)
    await session.flush()
    session.add_all(
        [
            CaseItem(case_id=case.id, name="Cheap", value=10, sort_order=0),
            CaseItem(case_id=case.id, name="Rare", value=1000, sort_order=1),
        ]
    )
    await session.commit()
    await session.refresh(case)
    return case


async def test_new_user_gets_starting_demo_tokens():
    async with engine_module.async_session() as session:
        user = await users_repo.get_or_create_user(session, tg_id=1, username="a", first_name="A")
        assert user.game_tokens > 0


async def test_add_game_tokens_increments_balance():
    async with engine_module.async_session() as session:
        user = await users_repo.get_or_create_user(session, tg_id=2, username="b", first_name="B")
        before = user.game_tokens
        user = await users_repo.add_game_tokens(session, user, 500)
        assert user.game_tokens == before + 500


async def test_list_cases_filters_by_category_and_orders_by_sort_order():
    async with engine_module.async_session() as session:
        session.add_all(
            [
                Case(category=CaseCategory.STARTER, code="c1", name="First", sort_order=2),
                Case(category=CaseCategory.STARTER, code="c2", name="Second", sort_order=1),
                Case(category=CaseCategory.SIGNATURE, code="c3", name="Other category", sort_order=0),
            ]
        )
        await session.commit()

        cases_list = await cases_repo.list_cases(session, CaseCategory.STARTER)
        assert [c.name for c in cases_list] == ["Second", "First"]


async def test_list_case_items_orders_by_value_desc():
    async with engine_module.async_session() as session:
        case = await _seed_case_with_items(session)
        items = await cases_repo.list_case_items(session, case.id)
        assert [i.name for i in items] == ["Rare", "Cheap"]


async def test_inventory_add_and_list_recent():
    async with engine_module.async_session() as session:
        user = await users_repo.get_or_create_user(session, tg_id=3, username="c", first_name="C")
        case = await _seed_case_with_items(session)

        await inventory_repo.add_items(session, user, case.name, [("Cheap", 10), ("Rare", 1000)], case_id=case.id)
        recent = await inventory_repo.list_recent(session, user, limit=10)

        assert len(recent) == 2
        assert {e.item_name for e in recent} == {"Cheap", "Rare"}
        assert all(e.case_name == "Seed Case" for e in recent)
