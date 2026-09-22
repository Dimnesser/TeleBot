"""Инициализация БД и фабрика сессий."""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.config import config
from bot.data.seed_items import SEED_ITEMS
from bot.database.models import Base, DepositItem

engine = create_async_engine(config.database_url)
async_session: async_sessionmaker[AsyncSession] = async_sessionmaker(engine, expire_on_commit=False)


def _ensure_sqlite_dir(database_url: str) -> None:
    if not database_url.startswith("sqlite"):
        return
    path_part = database_url.split("///", 1)[-1]
    if path_part and path_part != ":memory:":
        Path(path_part).parent.mkdir(parents=True, exist_ok=True)


async def init_db() -> None:
    _ensure_sqlite_dir(config.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _seed_items_if_empty()


async def _seed_items_if_empty() -> None:
    async with async_session() as session:
        result = await session.execute(select(DepositItem.id).limit(1))
        if result.scalar_one_or_none() is not None:
            return
        session.add_all(
            DepositItem(
                category=item.category,
                name=item.name,
                emoji=item.emoji,
                price_b=item.price_b,
                min_qty=item.min_qty,
                hot_stock_left=item.hot_stock_left,
                sort_order=item.sort_order,
            )
            for item in SEED_ITEMS
        )
        await session.commit()
