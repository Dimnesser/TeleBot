"""Операции с заявками на депозит."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import DepositCategory, DepositRequest, DepositRequestStatus, User


async def create_request(
    session: AsyncSession,
    user: User,
    category: DepositCategory,
    items: dict[int, int],
    buff: str | None,
    game_nickname: str,
    total_b: int,
    status: DepositRequestStatus = DepositRequestStatus.PENDING,
) -> DepositRequest:
    request = DepositRequest(
        user_id=user.id,
        category=category,
        items={str(item_id): qty for item_id, qty in items.items()},
        buff=buff,
        game_nickname=game_nickname,
        total_b=total_b,
        status=status,
    )
    session.add(request)
    await session.commit()
    await session.refresh(request)
    return request


async def get_request(session: AsyncSession, request_id: int) -> DepositRequest | None:
    return await session.get(DepositRequest, request_id)


async def count_status(session: AsyncSession, status: DepositRequestStatus) -> int:
    result = await session.execute(
        select(func.count()).select_from(DepositRequest).where(DepositRequest.status == status)
    )
    return result.scalar_one()


async def get_oldest_queued(session: AsyncSession) -> DepositRequest | None:
    result = await session.execute(
        select(DepositRequest)
        .where(DepositRequest.status == DepositRequestStatus.QUEUED)
        .order_by(DepositRequest.id.asc())  # id строго растёт — порядок очереди без ничьих
        .limit(1)
    )
    return result.scalar_one_or_none()


async def promote_to_pending(session: AsyncSession, request: DepositRequest) -> DepositRequest:
    request.status = DepositRequestStatus.PENDING
    await session.commit()
    await session.refresh(request)
    return request


async def resolve_request(
    session: AsyncSession,
    request: DepositRequest,
    status: DepositRequestStatus,
    admin_id: int,
) -> DepositRequest:
    request.status = status
    request.admin_id = admin_id
    request.resolved_at = datetime.utcnow()
    await session.commit()
    await session.refresh(request)
    return request
