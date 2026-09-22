"""Общие фикстуры тестов: подмена БД на in-memory SQLite перед каждым тестом."""
from __future__ import annotations

import pytest

import bot.database.engine as engine_module
from bot.database.models import Base
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


@pytest.fixture(autouse=True)
async def in_memory_db(monkeypatch):
    test_engine = create_async_engine("sqlite+aiosqlite://")
    test_session = async_sessionmaker(test_engine, expire_on_commit=False)

    monkeypatch.setattr(engine_module, "engine", test_engine)
    monkeypatch.setattr(engine_module, "async_session", test_session)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield test_session

    await test_engine.dispose()
