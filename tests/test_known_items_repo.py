"""Тесты объединённого каталога известных предметов (для целей апгрейдера)."""
from __future__ import annotations

from bot.database import engine as engine_module
from bot.database.models import Case, CaseCategory, CaseItem, DepositCategory, DepositItem
from bot.database.repo.known_items import list_known_items


async def test_list_known_items_merges_deposit_and_case_items():
    async with engine_module.async_session() as session:
        session.add(
            DepositItem(category=DepositCategory.BRAINROT, name="Kraken", emoji="🐙", price_b=3000, min_qty=1)
        )
        case = Case(category=CaseCategory.STARTER, code="c1", name="Test", is_openable=True)
        session.add(case)
        await session.flush()
        session.add(CaseItem(case_id=case.id, name="Dragon Cannelloni", value=973))
        await session.commit()

        items = await list_known_items(session)
        names = {item.name for item in items}
        assert "Kraken" in names
        assert "Dragon Cannelloni" in names


async def test_list_known_items_sorted_ascending_by_value():
    async with engine_module.async_session() as session:
        case = Case(category=CaseCategory.STARTER, code="c1", name="Test", is_openable=True)
        session.add(case)
        await session.flush()
        session.add_all(
            [
                CaseItem(case_id=case.id, name="Expensive", value=1000),
                CaseItem(case_id=case.id, name="Cheap", value=10),
            ]
        )
        await session.commit()

        items = await list_known_items(session)
        assert [item.value for item in items] == sorted(item.value for item in items)


async def test_list_known_items_dedupes_by_name_keeping_max_value():
    async with engine_module.async_session() as session:
        session.add(DepositItem(category=DepositCategory.HIRSY, name="Shared", emoji="x", price_b=50, min_qty=1))
        case = Case(category=CaseCategory.STARTER, code="c1", name="Test", is_openable=True)
        session.add(case)
        await session.flush()
        session.add(CaseItem(case_id=case.id, name="Shared", value=200))
        await session.commit()

        items = await list_known_items(session)
        shared = [item for item in items if item.name == "Shared"]
        assert len(shared) == 1
        assert shared[0].value == 200
