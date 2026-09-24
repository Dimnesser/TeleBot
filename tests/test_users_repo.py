"""get_or_create_user под параллельными запросами одного нового игрока.

Mini App при первом открытии шлёт несколько запросов разом; каждый видит
«игрока нет» и пытается его создать. Проверяется на файловой SQLite (как в
проде): у in-memory базы тестов одно общее соединение на все сессии.
"""
from __future__ import annotations

import asyncio

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bot.database.models import Base, User
from bot.database.repo.users import get_or_create_user


async def test_parallel_get_or_create_returns_one_user(tmp_path) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'db.sqlite'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async def first_request():
        async with sessions() as session:
            return (await get_or_create_user(session, 42, "new", "New")).id

    ids = await asyncio.gather(*(first_request() for _ in range(6)))
    assert len(set(ids)) == 1
    async with sessions() as session:
        assert (await session.execute(select(func.count(User.id)))).scalar_one() == 1
    await engine.dispose()
