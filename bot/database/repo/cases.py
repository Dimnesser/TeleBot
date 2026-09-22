"""Операции с каталогом кейсов и пулами дропа."""
from __future__ import annotations

from sqlalchemy import asc, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import Case, CaseCategory, CaseItem


async def list_cases(session: AsyncSession, category: CaseCategory) -> list[Case]:
    result = await session.execute(
        select(Case).where(Case.category == category).order_by(asc(Case.sort_order))
    )
    return list(result.scalars().all())


async def get_case(session: AsyncSession, case_id: int) -> Case | None:
    return await session.get(Case, case_id)


async def list_case_items(session: AsyncSession, case_id: int) -> list[CaseItem]:
    result = await session.execute(
        select(CaseItem).where(CaseItem.case_id == case_id).order_by(CaseItem.value.desc())
    )
    return list(result.scalars().all())
