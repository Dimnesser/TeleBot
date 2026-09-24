"""Операции с пользователями."""
from __future__ import annotations

import secrets

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import config
from bot.database.models import User


async def get_or_create_user(
    session: AsyncSession,
    tg_id: int,
    username: str | None,
    first_name: str | None,
    referral_code: str | None = None,
) -> User:
    result = await session.execute(select(User).where(User.tg_id == tg_id))
    user = result.scalar_one_or_none()
    if user:
        return user

    referred_by_id = None
    if referral_code:
        ref_result = await session.execute(select(User).where(User.referral_code == referral_code))
        referrer = ref_result.scalar_one_or_none()
        if referrer:
            referred_by_id = referrer.id

    user = User(
        tg_id=tg_id,
        username=username,
        first_name=first_name,
        balance=0,
        game_tokens=config.demo_starting_tokens,
        referral_code=secrets.token_hex(4).upper(),
        referred_by_id=referred_by_id,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def get_user_by_tg_id(session: AsyncSession, tg_id: int) -> User | None:
    result = await session.execute(select(User).where(User.tg_id == tg_id))
    return result.scalar_one_or_none()


async def add_game_tokens(session: AsyncSession, user: User, amount: int) -> User:
    user.game_tokens += amount
    await session.commit()
    await session.refresh(user)
    return user


async def add_balance(session: AsyncSession, user: User, amount: int) -> User:
    user.balance += amount
    await session.commit()
    await session.refresh(user)
    return user


async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    return await session.get(User, user_id)


async def count_referrals(session: AsyncSession, user: User) -> int:
    result = await session.execute(select(func.count()).select_from(User).where(User.referred_by_id == user.id))
    return result.scalar_one()


async def find_user(session: AsyncSession, query: str) -> User | None:
    """Поиск для админки: Telegram id или @username (без учёта регистра)."""
    q = query.strip()
    if q.lstrip("-").isdigit():
        return await get_user_by_tg_id(session, int(q))
    q = q.lstrip("@").lower()
    if not q:
        return None
    result = await session.execute(select(User).where(func.lower(User.username) == q))
    return result.scalar_one_or_none()
